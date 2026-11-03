"""The marriage answer and the spouse's income are stored encrypted (3e1 spec §3.3, §5.2).

Business intent: Form 122A-1 line 1 is a sworn answer in the form's words, so the server takes
only its four answers, never an old tax-filing status. The spouse's amounts are new data,
encrypted from the start and bounded as the filer's are; a blank box stays blank.
"""

from decimal import Decimal

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import IncomeInfo, IntakeSession, SpouseIncome
from apps.users.models import User

TEN_EMPTY = dict.fromkeys(IncomeInfo.SOURCE_FIELDS)


@pytest.fixture
def filer(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, IntakeSession.objects.create(user=user, district=district)


def _save(client, session, body):
    return client.patch(f"/api/intake/sessions/{session.pk}/", body, format="json")


def _raw(sql, session):
    with connection.cursor() as cursor:
        cursor.execute(sql, [session.pk])
        return cursor.fetchone()[0]


def test_a_marriage_answer_is_stored_as_ciphertext(filer):
    client, session = filer
    _save(client, session, {"income_info": {"marital_status": "married_together"}})
    raw = _raw("SELECT marital_status FROM income_info WHERE session_id = %s", session)
    assert "married_together" not in raw
    assert IncomeInfo.objects.get(session=session).marital_status == "married_together"


def test_a_spouse_amount_is_stored_as_ciphertext(filer):
    client, session = filer
    _save(client, session, {"spouse_income": {"monthly_gross_wages": "1800.00"}})
    raw = _raw("SELECT monthly_gross_wages FROM spouse_income WHERE session_id = %s", session)
    assert "1800" not in raw
    assert SpouseIncome.objects.get(session=session).monthly_gross_wages == Decimal("1800.00")


@pytest.mark.parametrize("answer", ["married_joint", "single", ""])
def test_an_old_tax_filing_status_is_refused(filer, answer):
    client, session = filer
    response = _save(client, session, {"income_info": {"marital_status": answer}})
    assert response.status_code == 400
    assert "marital_status" in response.data["income_info"]
    assert not IncomeInfo.objects.filter(session=session).exists()


@pytest.mark.parametrize("field", IncomeInfo.SOURCE_FIELDS)
@pytest.mark.parametrize(
    "amount",
    ["-1.00", "100000000.00", "12.345"],
    ids=["negative", "too_wide", "fraction_of_a_cent"],
)
def test_a_spouse_amount_is_bounded_as_the_filers(filer, field, amount):
    # Each of the ten is bounded by its own declaration, so each one is checked.
    client, session = filer
    assert _save(client, session, {"spouse_income": {field: amount}}).status_code == 400
    assert not SpouseIncome.objects.filter(session=session).exists()


@pytest.mark.parametrize("amount", ["NaN", "Infinity"], ids=["nan", "infinite"])
def test_a_spouse_amount_that_is_not_a_number_is_refused(filer, amount):
    # DRF's DecimalField refuses these whatever a field's kwargs, so one field stands for all ten.
    client, session = filer
    assert (
        _save(client, session, {"spouse_income": {"monthly_gross_wages": amount}}).status_code
        == 400
    )
    assert not SpouseIncome.objects.filter(session=session).exists()


def test_a_blank_spouse_box_is_null_not_zero(filer):
    client, session = filer
    sent = {**TEN_EMPTY, "monthly_gross_wages": "1000.00", "monthly_tips": "0"}
    reply = _save(client, session, {"spouse_income": sent}).data["spouse_income"]
    spouse = SpouseIncome.objects.get(session=session)
    assert (spouse.monthly_overtime, spouse.monthly_tips) == (None, Decimal("0.00"))
    assert (reply["monthly_overtime"], reply["monthly_tips"]) == (None, "0.00")


def test_a_changed_marriage_answer_and_spouse_amount_come_back_in_the_reply(filer):
    # The second save updates stored rows: its reply shows them as saved, not as read before.
    client, session = filer
    first = _save(
        client,
        session,
        {
            "income_info": {"marital_status": "married_together"},
            "spouse_income": {"monthly_gross_wages": "1000.00"},
        },
    )
    # Had the first save failed, the second would create the rows, and creating caches them.
    assert first.status_code == 200
    reply = _save(
        client,
        session,
        {
            "income_info": {"marital_status": "married_separately"},
            "spouse_income": {"monthly_gross_wages": "1200.00"},
        },
    ).data
    assert reply["income_info"]["marital_status"] == "married_separately"
    assert reply["spouse_income"]["monthly_gross_wages"] == "1200.00"


def test_the_spouses_income_stays_saved_when_the_marriage_answer_moves_away(filer):
    # Spec §5.1: away from living together, the spouse's figures stop counting but stay saved,
    # so they come back if the answer does.
    client, session = filer
    sent = {**TEN_EMPTY, "monthly_gross_wages": "1800.00", "monthly_pension": "250.00"}
    saved = _save(
        client,
        session,
        {"income_info": {"marital_status": "married_together"}, "spouse_income": sent},
    )
    assert saved.status_code == 200

    moved = _save(client, session, {"income_info": {"marital_status": "married_separately"}})

    assert moved.status_code == 200
    spouse = SpouseIncome.objects.get(session=session)
    assert (spouse.monthly_gross_wages, spouse.monthly_pension) == (
        Decimal("1800.00"),
        Decimal("250.00"),
    )
    assert moved.data["spouse_income"]["monthly_gross_wages"] == "1800.00"


def test_an_income_rows_str_never_shows_its_marriage_answer(filer):
    # __str__ reaches the admin and the logs, where the encrypted answer must not appear (P17).
    _, session = filer
    income = IncomeInfo.objects.create(session=session, marital_status="married_separately")
    assert "married" not in str(income)


def test_a_new_session_can_carry_its_spouse_income(filer):
    client, session = filer
    body = {
        "district": session.district_id,
        "current_step": 1,
        "spouse_income": {"monthly_gross_wages": "1000.00"},
    }
    created = client.post("/api/intake/sessions/", body, format="json")
    assert created.status_code == 201
    stored = SpouseIncome.objects.get(session_id=created.data["session"]["id"])
    assert stored.monthly_gross_wages == Decimal("1000.00")
