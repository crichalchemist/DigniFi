"""A filer who reopens the Income step keeps the income they saved (DIG-41).

Only ``IncomeInfo.monthly_income`` (six months) is stored. The step's per-source boxes
never reach the server, so the step shows the saved total the API reports, and saves send
``monthly_income`` alone.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import IncomeInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def filer_session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    filer = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=filer, district=district)
    client = APIClient()
    client.force_authenticate(user=filer)
    return client, session


@pytest.mark.django_db
class TestIncomeStepResume:
    def test_returning_filer_gets_their_saved_monthly_income_total(self, filer_session):
        client, session = filer_session
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            monthly_income=[3100, 3300, 3200, 3200, 3150, 3250],
        )

        resp = client.get(f"/api/intake/sessions/{session.pk}/")

        assert resp.status_code == 200
        assert resp.json()["income_info"]["total_monthly_income"] == 3200.0

    def test_saved_total_is_shown_to_the_cent(self, filer_session):
        client, session = filer_session
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            monthly_income=[1000, 1000, 1000, 1000, 1000, 1001],
        )

        resp = client.get(f"/api/intake/sessions/{session.pk}/")

        assert resp.json()["income_info"]["total_monthly_income"] == 1000.17

    def test_row_without_months_reports_zero_instead_of_breaking_the_session_read(
        self, filer_session
    ):
        client, session = filer_session
        IncomeInfo.objects.create(session=session, marital_status="single", monthly_income=[])

        resp = client.get(f"/api/intake/sessions/{session.pk}/")

        assert resp.status_code == 200
        assert resp.json()["income_info"]["total_monthly_income"] == 0.0

    def test_saving_income_amounts_keeps_household_details(self, filer_session):
        client, session = filer_session
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_joint",
            number_of_dependents=2,
            monthly_income=[2500] * 6,
        )

        resp = client.patch(
            f"/api/intake/sessions/{session.pk}/",
            {"income_info": {"monthly_income": [4000] * 6}},
            format="json",
        )

        assert resp.status_code == 200
        income = IncomeInfo.objects.get(session=session)
        assert income.monthly_income == [4000] * 6
        assert income.marital_status == "married_joint"
        assert income.number_of_dependents == 2

    def test_a_wizard_created_row_echoed_back_whole_would_strand_the_filer(self, filer_session):
        # Why the wizard sends monthly_income alone: a row the wizard created has a blank
        # marital_status, and sending the row back as read is a 400 that strands the filer.
        client, session = filer_session
        IncomeInfo.objects.create(session=session, monthly_income=[3200] * 6)

        resp = client.patch(
            f"/api/intake/sessions/{session.pk}/",
            {
                "income_info": {
                    "marital_status": "",
                    "number_of_dependents": 0,
                    "monthly_income": [3200] * 6,
                }
            },
            format="json",
        )

        assert resp.status_code == 400
