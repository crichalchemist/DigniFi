"""A filer's income is stored by source, as the Income step's ten boxes name it (spec §5.5).

Business intent: the court forms ask for each kind of income on its own line, and the means
test leaves Social Security out, so a single total can't fill them. A box the filer left
empty stays empty, never $0, because a $0 the filer never gave would be sworn on a form.
The old six-month total is kept, read-only, for one release: it is the only record of what
an earlier filer entered, and the Income step shows it while asking them to split it.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession
from apps.users.models import User

SPLIT_BY_SOURCE = "Enter your income by source on the Income step."

TEN_EMPTY = {
    "monthly_gross_wages": None,
    "monthly_overtime": None,
    "monthly_tips": None,
    "monthly_rental_income": None,
    "monthly_pension": None,
    "monthly_social_security": None,
    "monthly_unemployment": None,
    "monthly_child_support": None,
    "monthly_alimony": None,
    "monthly_other_income": None,
}


@pytest.fixture
def filer_session(db):
    # The real ILND data: its name is one of the court forms' district choices, and preparing
    # forms works the means test out against its median income.
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    district = District.objects.get(code="ilnd")
    filer = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=filer, district=district)
    client = APIClient()
    client.force_authenticate(user=filer)
    return client, session


def _session_url(session, action=""):
    return f"/api/intake/sessions/{session.pk}/{action}"


@pytest.mark.django_db
class TestIncomeBySource:
    def test_new_filer_saves_income_by_source_without_a_total(self, filer_session):
        client, session = filer_session

        resp = client.patch(
            _session_url(session),
            {
                "income_info": {
                    **TEN_EMPTY,
                    "monthly_gross_wages": "3200.00",
                    "monthly_social_security": "0",
                }
            },
            format="json",
        )

        assert resp.status_code == 200
        income = IncomeInfo.objects.get(session=session)
        assert income.monthly_gross_wages == Decimal("3200.00")
        assert income.monthly_social_security == Decimal("0.00")
        # A box the filer left empty is stored empty, not as $0.
        assert income.monthly_overtime is None
        assert income.monthly_other_income is None
        # The old total is never written again.
        assert income.monthly_income is None
        assert resp.data["income_info"]["total_monthly_income"] == 3200.0

    def test_returning_filer_gets_each_saved_amount_back(self, filer_session):
        client, session = filer_session
        IncomeInfo.objects.create(
            session=session,
            monthly_gross_wages=Decimal("3100.50"),
            monthly_tips=Decimal("0.00"),
            monthly_social_security=Decimal("900.25"),
        )

        resp = client.get(_session_url(session))

        income = resp.json()["income_info"]
        assert income["monthly_gross_wages"] == "3100.50"
        assert income["monthly_tips"] == "0.00"
        assert income["monthly_overtime"] is None
        # The total adds every source the filer gave, Social Security included.
        assert income["total_monthly_income"] == 4000.75

    def test_a_saved_total_stays_readable_so_the_income_step_can_ask_to_split_it(
        self, filer_session
    ):
        client, session = filer_session
        IncomeInfo.objects.create(session=session, monthly_income=[3100, 3300, 3200] * 2)

        income = client.get(_session_url(session)).json()["income_info"]

        assert income["monthly_income"] == [3100, 3300, 3200] * 2
        assert {field: income[field] for field in TEN_EMPTY} == TEN_EMPTY
        assert income["total_monthly_income"] is None

    def test_a_total_sent_by_an_old_page_is_not_stored(self, filer_session):
        client, session = filer_session
        IncomeInfo.objects.create(session=session, monthly_income=[2500] * 6)

        resp = client.patch(
            _session_url(session),
            {"income_info": {"monthly_income": [4000] * 6, "monthly_gross_wages": "4000"}},
            format="json",
        )

        assert resp.status_code == 200
        income = IncomeInfo.objects.get(session=session)
        assert income.monthly_income == [2500] * 6
        assert income.monthly_gross_wages == Decimal("4000.00")

    def test_saving_income_amounts_keeps_household_details(self, filer_session):
        client, session = filer_session
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_joint",
            number_of_dependents=2,
            monthly_gross_wages=Decimal("2500.00"),
        )

        resp = client.patch(
            _session_url(session),
            {"income_info": {**TEN_EMPTY, "monthly_gross_wages": "4000"}},
            format="json",
        )

        assert resp.status_code == 200
        income = IncomeInfo.objects.get(session=session)
        assert income.monthly_gross_wages == Decimal("4000.00")
        assert income.marital_status == "married_joint"
        assert income.number_of_dependents == 2

    def test_a_wizard_created_row_echoed_back_whole_would_strand_the_filer(self, filer_session):
        # Why the wizard sends the ten amounts alone: a row the wizard created has a blank
        # marital_status, and sending the row back as read is a 400 that strands the filer.
        client, session = filer_session
        IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3200.00"))

        resp = client.patch(
            _session_url(session),
            {
                "income_info": {
                    "marital_status": "",
                    "number_of_dependents": 0,
                    "monthly_gross_wages": "3200.00",
                }
            },
            format="json",
        )

        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "amount",
        ["-1.00", "100000000.00", "NaN", "Infinity", "12.345"],
        ids=["negative", "too_wide", "nan", "infinite", "fraction_of_a_cent"],
    )
    def test_an_income_amount_outside_the_column_is_refused(self, filer_session, amount):
        client, session = filer_session

        resp = client.patch(
            _session_url(session),
            {"income_info": {"monthly_pension": amount}},
            format="json",
        )

        assert resp.status_code == 400
        assert not IncomeInfo.objects.filter(session=session).exists()

    def test_the_largest_amount_the_column_holds_is_saved(self, filer_session):
        client, session = filer_session

        resp = client.patch(
            _session_url(session),
            {"income_info": {"monthly_pension": "99999999.99"}},
            format="json",
        )

        assert resp.status_code == 200
        assert IncomeInfo.objects.get(session=session).monthly_pension == Decimal("99999999.99")


def _complete(session):
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    ExpenseInfo.objects.create(session=session)
    session.status = "completed"
    session.save()


def test_legacy_income_total_must_be_split_before_forms_print(filer_session):
    client, session = filer_session
    IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)
    _complete(session)
    generate = {"session_id": session.pk, "form_type": "schedule_i"}

    refused = client.post("/api/forms/generate/", generate, format="json")
    assert refused.status_code == 422
    assert refused.data == {"form_type": "schedule_i", "error": SPLIT_BY_SOURCE}
    # Every form waits for the split, since each call works the means test out first.
    every_form = client.post("/api/forms/generate_all/", {"session_id": session.pk}, format="json")
    assert every_form.status_code == 422
    assert every_form.data == {"error": SPLIT_BY_SOURCE}

    # The filer splits the total on the Income step and completes the intake again.
    split = client.patch(
        _session_url(session),
        {"income_info": {**TEN_EMPTY, "monthly_gross_wages": "3000"}},
        format="json",
    )
    assert split.status_code == 200
    assert client.post(_session_url(session, "complete/")).status_code == 200
    assert client.post("/api/forms/generate/", generate, format="json").status_code == 200
