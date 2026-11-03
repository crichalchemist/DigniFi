"""Schedule J asks every line and says "Answer every question".

A line the filer leaves empty is $0 and prints blank, line 3 never starts answered, and
every new amount is filer data, so it is encrypted (3e2 spec §5).
"""

from decimal import Decimal

import pytest
from django.db import connection

from apps.forms.services.derivations import DERIVATIONS
from apps.intake.models import ExpenseInfo

NEW_LINES = {
    "real_estate_taxes": "210.00",
    "home_insurance": "15.00",
    "hoa_dues": "75.00",
    "personal_care": "40.00",
    "entertainment": "45.00",
    "charitable_contributions": "50.00",
    "taxes_not_deducted": "200.00",
    "support_others": "100.00",
    "other_property_mortgages": "600.00",
    "other_property_taxes": "90.00",
    "other_property_insurance": "30.00",
    "other_property_upkeep": "25.00",
    "other_property_hoa_dues": "20.00",
}  # sums to 1500.00


def _url(session):
    return f"/api/intake/sessions/{session.pk}/"


def test_the_new_schedule_j_lines_reach_the_total_every_form_prints(filer_session):
    client, session = filer_session
    client.patch(
        _url(session), {"expense_info": {"rent_or_mortgage": "1000.00", **NEW_LINES}}, format="json"
    )
    assert client.get(_url(session)).json()["expense_info"]["total_monthly_expenses"] == 2500.0
    # the one function behind J 22a/22c/23b, 106Sum 5, 103B 6
    assert DERIVATIONS["fee_waiver_monthly_expenses"](session) == "2500.00"


def test_an_empty_expenses_body_stores_26_zero_amounts_and_leaves_line_3_unanswered(
    filer_session,
):
    client, session = filer_session
    response = client.patch(_url(session), {"expense_info": {}}, format="json")
    assert response.status_code == 200
    reply = response.json()["expense_info"]
    row = ExpenseInfo.objects.get(session=session)
    assert len(ExpenseInfo.AMOUNT_FIELDS) == 26
    assert all(Decimal(getattr(row, f)) == 0 for f in ExpenseInfo.AMOUNT_FIELDS)
    assert row.expenses_include_others is None and reply["expenses_include_others"] is None
    assert all(reply[f] == "" for f in ExpenseInfo.SPECIFY_FIELDS)
    assert reply["rent_or_mortgage"] == "0.00"


def test_line_3_takes_only_yes_no_or_null(filer_session):
    client, session = filer_session
    refused = client.patch(
        _url(session), {"expense_info": {"expenses_include_others": "maybe"}}, format="json"
    )
    assert refused.status_code == 400
    accepted = client.patch(
        _url(session), {"expense_info": {"expenses_include_others": "yes"}}, format="json"
    )
    assert accepted.status_code == 200


@pytest.mark.parametrize(
    "field", ["taxes_specify", "support_others_specify", "other_expenses_specify"]
)
def test_a_specify_text_over_100_characters_is_refused(filer_session, field):
    client, session = filer_session
    response = client.patch(_url(session), {"expense_info": {field: "x" * 101}}, format="json")
    assert response.status_code == 400


@pytest.mark.parametrize(
    "field,value,plain",
    [
        *[(name, amount, amount) for name, amount in NEW_LINES.items()],
        *[
            (name, "455.00", "455.00")
            for name in ExpenseInfo.AMOUNT_FIELDS
            if name not in NEW_LINES
        ],
        *[
            (name, "IRS installment agreement, 2025 tax", "IRS")
            for name in ExpenseInfo.SPECIFY_FIELDS
        ],
        ("expenses_include_others", "yes", None),
    ],
)
def test_every_new_expense_column_is_ciphertext(filer_session, field, value, plain):
    client, session = filer_session
    client.patch(_url(session), {"expense_info": {field: value}}, format="json")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {field} FROM expense_info WHERE session_id = %s", [session.pk])
        raw = cursor.fetchone()[0]
    assert raw.startswith("gAAAAA") and (plain is None or plain not in raw)
