"""The records behind the questions Schedules D, E/F, G and H ask (3c3 Task 1)."""

import json
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader

from apps.forms.services.text_fit import fit
from apps.forms.services.widgets import template_widgets
from apps.intake.models import AssetInfo, ClaimAnswers, Codebtor, DebtInfo, ExecutoryContract

CIPHERTEXT = "gAAAAA"  # every Fernet token starts so

ADDRESS = ["street_address", "street_2", "city", "state", "zip_code", "outside_us"]
DEBT_COLUMNS = [
    *ADDRESS,
    "home_payment_line",
    "collateral_who",
    "offset_answer",
    "community_debt",
    "lien",
    "claim_status",
    "notice_parties",
]
CONTRACT_COLUMNS = [*ADDRESS, "lease_kind", "monthly_payment", "owes_now"]
CODEBTOR_COLUMNS = ["street_2", "outside_us", "links"]


def _raw(table, columns, pk):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {', '.join(columns)} FROM {table} WHERE id = %s", [pk])
        return cursor.fetchone()


def _debt(session, **extra):
    return DebtInfo.objects.create(
        session=session,
        creditor_name="Demo Card Services",
        debt_type="credit_card",
        amount_owed=Decimal("100.00"),
        **extra,
    )


def test_every_new_claim_answer_is_stored_as_ciphertext(filer):
    _, session = filer
    debt = _debt(
        session,
        street_address="12 Demo Street",
        street_2="Unit 4",
        city="Demoville",
        state="IL",
        zip_code="60601",
        outside_us=True,
        home_payment_line="first",
        collateral_who="only_you",
        offset_answer="no",
        community_debt="yes",
        lien=json.dumps({"kinds": ["agreement"], "other": ""}),
        claim_status=json.dumps(["disputed"]),
        notice_parties=json.dumps([]),
    )
    row = _raw("debt_info", DEBT_COLUMNS, debt.pk)
    assert len(row) == 13
    assert all(str(v).startswith(CIPHERTEXT) for v in row)

    contract = ExecutoryContract.objects.create(
        session=session,
        counterparty_name="Demo Landlord",
        street_address="12 Demo Street",
        street_2="Unit 4",
        city="Demoville",
        state="IL",
        zip_code="60601",
        outside_us=True,
        lease_kind="vehicle",
        monthly_payment=Decimal("250.00"),
        owes_now="no",
    )
    row = _raw("executory_contracts", CONTRACT_COLUMNS, contract.pk)
    assert all(str(v).startswith(CIPHERTEXT) for v in row)

    codebtor = Codebtor.objects.create(
        session=session,
        name="Demo Person",
        street_2="Unit 4",
        outside_us=True,
        links=json.dumps([{"kind": "debt", "id": 1}]),
    )
    row = _raw("codebtors", CODEBTOR_COLUMNS, codebtor.pk)
    assert all(str(v).startswith(CIPHERTEXT) for v in row)

    answers = ClaimAnswers.objects.create(session=session)
    answers.merge({"community_state": "Demo State"})
    answers.save()
    (stored,) = _raw("claim_answers", ["answers"], answers.pk)
    assert stored.startswith(CIPHERTEXT)
    assert "Demo State" not in stored

    # The foreign keys and the id counter stay plaintext.
    assert _raw("debt_info", ["secured_by_id", "next_notice_party_id"], debt.pk) == (None, 1)


def test_the_status_flags_no_form_ever_read_are_gone():
    names = {f.name for f in DebtInfo._meta.get_fields()}
    assert names.isdisjoint({"is_contingent", "is_unliquidated", "is_disputed"})


def test_a_new_contract_and_codebtor_store_no_type_or_relationship_unless_sent(filer):
    _, session = filer
    contract = ExecutoryContract.objects.create(session=session, counterparty_name="Demo Co")
    codebtor = Codebtor.objects.create(session=session, name="Demo Person")
    contract.refresh_from_db()
    codebtor.refresh_from_db()
    assert contract.contract_type == ""
    assert codebtor.relationship == ""


def test_the_claims_migration_reverses_with_the_three_flags_false(db):
    loader = MigrationLoader(connection)
    migration = loader.get_migration("intake", "0040_claims_questions")
    assert all(op.reversible for op in migration.operations)
    state = loader.project_state(("intake", "0039_debtinfo_no_ordering"))
    old = state.models[("intake", "debtinfo")].fields
    assert all(old[n].default is False for n in ("is_contingent", "is_unliquidated", "is_disputed"))
    contract = state.models[("intake", "executorycontract")].fields
    assert contract["contract_type"].default == "contract"
    codebtor = state.models[("intake", "codebtor")].fields
    assert codebtor["relationship"].default == "other"


def test_store_notice_parties_never_reuses_an_id_and_keeps_a_sent_id_only_once(filer):
    _, session = filer
    debt = _debt(session)
    saved = debt.store_notice_parties([{"name": "A"}, {"name": "B"}])
    assert [p["id"] for p in saved] == [1, 2]
    assert debt.next_notice_party_id == 3

    saved = debt.store_notice_parties([{"id": 2, "name": "B"}])
    assert [p["id"] for p in saved] == [2]

    saved = debt.store_notice_parties([{"id": 2}, {"id": 2}])
    assert [p["id"] for p in saved] == [2, 3]

    debt.store_notice_parties([])
    saved = debt.store_notice_parties([{"name": "C"}])
    assert saved[0]["id"] > 3

    party = saved[0]
    assert set(party) == {"id", *DebtInfo.NOTICE_PARTY_KEYS}
    assert party["outside_us"] is False
    assert party["street_2"] == ""

    assert debt.store_notice_parties(None) is None
    assert debt.notice_parties is None
    assert debt.get_notice_parties() is None


def test_every_text_key_of_the_claim_answers_has_a_limit():
    text_keys = {
        key
        for key in ClaimAnswers.KEYS
        if key.startswith("community_")
        and key not in {"community_lived", "community_spouse_lived_with"}
        and key != "community_spouse_outside_us"
    }
    assert set(ClaimAnswers.TEXT_LIMITS) == text_keys
    assert ClaimAnswers.TEXT_LIMITS["community_spouse_state"] == 2


def test_a_debts_text_never_carries_the_creditor_or_address(filer):
    _, session = filer
    debt = _debt(session, street_address="12 Demo Street")
    text = str(debt)
    assert "Demo Card Services" not in text
    assert "12 Demo Street" not in text
    assert text == f"DebtInfo {debt.pk} (Credit Card, Consumer Debt)"
    assert str(ClaimAnswers(session=session)) == f"ClaimAnswers (Session: {session.pk})"


def _narrowest_date_box(template):
    boxes = [
        w for w in template_widgets(template) if w.full_name.startswith("Date debt was incurred")
    ]
    return min(boxes, key=lambda w: w.width)


def test_the_date_bound_is_the_longest_range_the_narrowest_box_prints():
    widget = _narrowest_date_box("form_b106d.pdf")
    assert widget.width == pytest.approx(50.0, abs=0.1)
    assert widget.page in (1, 2)
    longest = "00/0000-00/0000"
    result = fit(widget, "form_b106d.pdf", longest)
    assert result is not None
    assert result[1] == 6.0
    assert len(longest) == DebtInfo.DATE_INCURRED_MAX_LENGTH
    assert fit(widget, "form_b106d.pdf", "00/0000-00/00000") is None
    ef = _narrowest_date_box("form_b106ef.pdf")
    assert fit(ef, "form_b106ef.pdf", longest) is not None


def test_a_debt_can_secure_to_an_asset_row(filer):
    # The link is a plain foreign key that a deleted property clears, never the debt.
    _, session = filer
    asset = AssetInfo.objects.create(session=session, current_value=Decimal("1.00"))
    debt = _debt(session, secured_by=asset)
    asset.delete()
    debt.refresh_from_db()
    assert debt.secured_by_id is None
