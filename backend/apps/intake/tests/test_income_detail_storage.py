"""The Income step's new answers are stored encrypted (3e2 spec §4, §6).

Business intent: each new Income step answer is the filer's own, stored encrypted, and nothing
starts answered. A missing answer saves for Complete to name, and only a value no answer can
have is refused.
"""

# ruff: noqa: F811
from decimal import Decimal

import pytest

from apps.intake.models import IncomeInfo, IntakeSession
from apps.intake.tests.test_spouse_and_marriage_storage import (  # noqa: F401, F811
    _raw,
    _save,
    filer,
)

GIG = {
    "kind": "business",
    "description": "Rideshare and delivery driving",
    "gross": "4200.00",
    "expenses": "830.00",
    "current_gross": None,
    "current_expenses": None,
}
RENTAL = {
    **GIG,
    "kind": "rental",
    "description": "2-flat, 1800 W Example Ave",
    "gross": "1200.00",
    "expenses": "300.00",
}


def _entries(client, session, rows, person="income_info"):
    response = _save(client, session, {person: {"business_and_rental": rows}})
    assert response.status_code == 200, response.data
    return response.data[person]["business_and_rental"]


@pytest.mark.parametrize("person", ["income_info", "spouse_income"])
def test_a_gig_drivers_entry_saves_with_an_id_and_comes_back_in_the_order_sent(filer, person):
    client, session = filer
    saved = _entries(client, session, [RENTAL, GIG], person)
    assert [e["description"] for e in saved] == [RENTAL["description"], GIG["description"]]
    assert [e["id"] for e in saved] == [1, 2]
    assert saved[1] == {"id": 2, **GIG}


def test_an_entry_id_is_never_reused(filer):
    client, session = filer
    first = _entries(client, session, [GIG, RENTAL])
    kept = _entries(client, session, [first[1]])  # GIG (id 1) removed
    assert [e["id"] for e in _entries(client, session, [*kept, GIG])] == [2, 3]


def test_an_id_repeated_within_one_list_keeps_the_first_row_and_gives_the_next_a_new_id(filer):
    client, session = filer
    first = _entries(client, session, [GIG, RENTAL])
    saved = _entries(client, session, [first[0], first[0]])
    assert [e["id"] for e in saved] == [1, 3]


def test_the_sessions_total_monthly_income_counts_entries_alone(filer):
    client, session = filer
    _entries(client, session, [GIG])  # 4200.00 less 830.00, and nothing else on the step
    income = client.get(f"/api/intake/sessions/{session.pk}/").json()["income_info"]
    assert income["total_monthly_income"] == 3370.0


def test_a_missing_entry_answer_saves_as_null(filer):
    client, session = filer
    [entry] = _entries(client, session, [{"kind": "business"}])
    assert entry == {
        "id": 1,
        "kind": "business",
        "description": None,
        "gross": None,
        "expenses": None,
        "current_gross": None,
        "current_expenses": None,
    }


def test_a_half_answered_entry_saves_when_the_session_is_created(db, filer):
    # A create path, not only a partial PATCH: a missing answer saves, and Complete names it.
    client, session = filer
    response = client.post(
        "/api/intake/sessions/",
        {
            "district": session.district_id,
            "income_info": {"business_and_rental": [{"kind": "rental"}]},
            "spouse_income": {"business_and_rental": [{"description": "Food truck"}]},
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    [mine] = response.data["session"]["income_info"]["business_and_rental"]
    assert (mine["id"], mine["kind"], mine["gross"]) == (1, "rental", None)
    [theirs] = response.data["session"]["spouse_income"]["business_and_rental"]
    assert (theirs["kind"], theirs["description"]) == (None, "Food truck")


@pytest.mark.parametrize(
    "rows",
    [
        [GIG] * 11,
        [{**GIG, "kind": "farm"}],
        [{**GIG, "description": "x" * 201}],
        [{**GIG, "gross": "-1.00"}],
        [{**GIG, "expenses": "100000000.00"}],
    ],
    ids=["eleventh_entry", "unknown_kind", "long_description", "negative", "too_wide"],
)
def test_a_value_no_answer_can_have_is_refused(filer, rows):
    client, session = filer
    assert _save(client, session, {"income_info": {"business_and_rental": rows}}).status_code == 400


@pytest.mark.parametrize("field", ["income_now_different", "assistance_answer"])
def test_a_yes_no_answer_takes_only_yes_no_or_null(filer, field):
    client, session = filer
    assert _save(client, session, {"income_info": {field: "maybe"}}).status_code == 400
    assert _save(client, session, {"spouse_income": {field: "maybe"}}).status_code == 400
    assert _save(client, session, {"income_info": {field: None}}).status_code == 200


def test_no_new_question_starts_answered(filer):
    client, session = filer
    income = _save(client, session, {"income_info": {"monthly_gross_wages": "1.00"}}).data[
        "income_info"
    ]
    assert income["business_and_rental"] is None
    assert income["income_now_different"] is None and income["assistance_answer"] is None
    assert all(
        income[f] is None for f in (*IncomeInfo.CURRENT_FIELDS, *IncomeInfo.DEDUCTION_FIELDS)
    )
    assert income["income_period_end"] is None


def test_saving_the_list_clears_a_legacy_rental_figure_and_a_body_without_it_leaves_it(filer):
    client, session = filer
    IncomeInfo.objects.create(session=session, monthly_rental_income=Decimal("900.00"))
    _save(client, session, {"income_info": {"monthly_gross_wages": "1.00"}})
    assert IncomeInfo.objects.get(session=session).monthly_rental_income == Decimal("900.00")
    _entries(client, session, [])
    assert IncomeInfo.objects.get(session=session).monthly_rental_income is None


@pytest.mark.parametrize("person", ["income_info", "spouse_income"])
def test_a_write_of_the_legacy_rental_figure_is_ignored(filer, person):
    client, session = filer
    response = _save(
        client, session, {person: {"monthly_rental_income": "500.00", "monthly_tips": "1.00"}}
    )
    assert response.status_code == 200
    assert response.data[person]["monthly_rental_income"] is None


def test_the_income_steps_save_never_changes_a_deduction_and_the_reverse(filer):
    client, session = filer
    _save(
        client,
        session,
        {"income_info": {"payroll_tax": "400.00", "payroll_other_specify": "Parking"}},
    )
    _save(
        client,
        session,
        {"income_info": {"monthly_gross_wages": "3200.00", "business_and_rental": []}},
    )
    row = IncomeInfo.objects.get(session=session)
    assert (row.payroll_tax, row.payroll_other_specify) == (Decimal("400.00"), "Parking")
    _save(client, session, {"income_info": {"payroll_tax": "410.00"}})
    row = IncomeInfo.objects.get(session=session)
    assert (row.monthly_gross_wages, row.get_entries()) == (Decimal("3200.00"), [])


@pytest.mark.parametrize(
    "field", ["payroll_other_specify", "cash_assistance_kind", "noncash_assistance_kind"]
)
def test_a_text_answer_over_100_characters_is_refused(filer, field):
    client, session = filer
    assert _save(client, session, {"income_info": {field: "x" * 101}}).status_code == 400


# Every encrypted IncomeDetail column (§13 "every migrated or new column is stored as ciphertext").
NEW_AMOUNTS = (
    "monthly_interest_and_dividends",
    *IncomeInfo.CURRENT_FIELDS,
    *IncomeInfo.DEDUCTION_FIELDS,
    "cash_assistance_amount",
    "noncash_assistance_value",
)
NEW_TEXTS = ("payroll_other_specify", "cash_assistance_kind", "noncash_assistance_kind")


@pytest.mark.parametrize("person", ["income_info", "spouse_income"])  # each is also its db_table
@pytest.mark.parametrize(
    "field,value,plain",
    [
        *[(f, "125.00", "125.00") for f in NEW_AMOUNTS],
        *[(f, "SNAP (food stamps)", "SNAP") for f in NEW_TEXTS],
        ("income_now_different", "yes", None),
        ("assistance_answer", "no", None),
        ("business_and_rental", [GIG], "Rideshare"),
    ],
)
def test_every_new_income_column_is_ciphertext(filer, person, field, value, plain):
    client, session = filer
    assert _save(client, session, {person: {field: value}}).status_code == 200
    raw = _raw(f"SELECT {field} FROM {person} WHERE session_id = %s", session)
    assert raw.startswith("gAAAAA") and (plain is None or plain not in raw)


def test_a_session_is_unchanged_by_a_failed_list(filer):
    client, session = filer
    _entries(client, session, [GIG])
    refused = _save(
        client, session, {"income_info": {"business_and_rental": [{**GIG, "kind": "farm"}]}}
    )
    assert refused.status_code == 400
    assert IncomeInfo.objects.get(session=session).get_entries()[0]["id"] == 1
    assert IntakeSession.objects.filter(pk=session.pk).exists()
