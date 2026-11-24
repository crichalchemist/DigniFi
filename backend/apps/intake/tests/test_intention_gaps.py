"""
Form 108's open choices and the claims texts too long for their boxes, as details in Complete's
list (forms step 4e, 4e-R4, 4e-R11, E4, R-EXPLAIN).

Business intent: the filer decides what happens to property that secures a debt, and DigniFi only
informs. A choice left open, or "[explain]" with no words, prints no choice on Form 108, so Review
and the dashboard say so, but never as something Complete waits for. A creditor's or lessor's name,
a property description and the "[explain]" words are stored as typed; a text over its box's cap,
or one a box truly can't take, is listed naming the form, so Review lists every text Generate
refuses, and never names a form the row doesn't print on.
"""

import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.services.explain_split import split_explain
from apps.forms.services.intention_fit import too_long_texts
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong
from apps.intake import intentions
from apps.intake.claim_rows import claim_list_of
from apps.intake.completion import Gap, completion_gaps
from apps.intake.intentions import (
    CLAIM_TEXT_KEYS,
    INTENTION_GAP_EXPLAIN,
    INTENTION_GAP_NONE,
    INTENTION_GAP_UNDECIDED,
    LEASE_GAP_NONE,
    LEASE_GAP_UNDECIDED,
    ROW_BOXES,
    claim_text_gaps,
    contract_text_list,
    intention_step_gaps,
    row_cap,
)
from apps.intake.models import AssetInfo, DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.schedule_i import DETAIL_TOO_LONG
from apps.intake.tests.builders import (
    answer_household,
    answer_intentions,
    complete_contract,
    complete_debt,
    finish_intake,
    linked_lease,
    linked_loan,
)
from apps.users.models import User

SCHEMAS = settings.BASE_DIR.parent / "data" / "forms" / "schemas"
CASES = (
    settings.BASE_DIR.parent
    / "frontend"
    / "src"
    / "components"
    / "wizard"
    / "steps"
    / "plans"
    / "claimTextRowCases.json"
)

# Sized by measure (each test asserts the measure it relies on): Schedule D's name box refuses a
# word of 26 W's and Form 108's one of 34, so 30 W's fit Form 108 but not Schedule D.
WIDE_NAME = "W" * 30
# Fits Schedule D's property box and Form 108's row 1 box, but not the Part 1 sheet's 104 pt column.
SHEET_WORD = "W" * 15


@pytest.fixture
def district(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


@pytest.fixture
def filer(district):
    user = User.objects.create_user(username="planfiler", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def session(filer, district):
    _, user = filer
    session = IntakeSession.objects.create(user=user, district=district, current_step=9)
    DebtorInfo.objects.create(
        session=session,
        first_name="Demo",
        last_name="Filer",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="demo.filer@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("3000.00")
    )
    return session


def _vehicle(session, description="Demo car"):
    """A Schedule A/B line 3 row with every answer the Assets step asks."""
    row = AssetInfo(
        session=session,
        ab_line="3",
        description=description,
        current_value=Decimal("5000.00"),
        entire_value=Decimal("5000.00"),
    )
    row.set_details({"who": "only_you", "make": "Demo", "lives_here": None})
    row.save()
    return row


def _secured(session, name="Demo Auto Finance", description="Demo car"):
    """A confirmed secured debt on its own vehicle row of Schedule A/B."""
    row = _vehicle(session, description=description)
    return linked_loan(session, row, "100", creditor_name=name, collateral_description=description)


def _lease(session, name="Demo Leasing", kind="vehicle", description="Demo car lease"):
    return complete_contract(
        session, counterparty_name=name, lease_kind=kind, description=description
    )


def _choose(session, debt, **entry):
    answer_intentions(session, secured={str(debt.pk): entry})


def _text_gaps(session, step):
    return [g for g in claim_text_gaps(session) if g.step == step]


def _too_long(label_key, *forms):
    words = " and ".join(intentions.FORM_WORDS[f] for f in forms)
    return DETAIL_TOO_LONG.format(label=intentions.CLAIM_TEXT_LABELS[label_key], form=words)


def _refuses(form_type, values) -> bool:
    try:
        PDFFormFiller().check(form_type, values)
    except ValueTooLong:
        return True
    return False


# ── The open choices (step `plans`) ──────────────────────────────────────


def test_each_open_row_is_one_detail_in_form_108s_order(session):
    zeta = _secured(session, name="Zeta Auto Credit")
    alpha = _secured(session, name="Alpha Bank")
    _lease(session, name="Demo Leasing")
    _choose(session, alpha, intention="undecided")

    gaps = intention_step_gaps(session)

    # Schedule D lists Alpha before Zeta (ordered_debts), then Part 2's lease
    assert [str(g) for g in gaps] == [
        INTENTION_GAP_UNDECIDED.format(name="Alpha Bank"),
        INTENTION_GAP_NONE.format(name="Zeta Auto Credit"),
        LEASE_GAP_NONE.format(name="Demo Leasing"),
    ]
    assert {(g.step, g.kind, g.forms) for g in gaps} == {("plans", Gap.DETAIL, ("form_108",))}
    assert zeta.pk != alpha.pk


@pytest.mark.parametrize("words", [None, "", "   "], ids=["no-words", "empty", "spaces"])
def test_retain_explain_with_blank_words_asks_for_them(session, words):
    debt = _secured(session, name="Demo Auto Finance")
    entry = {"intention": "retain_explain"} | ({} if words is None else {"explain": words})
    answer_intentions(session, secured={str(debt.pk): entry})

    (gap,) = intention_step_gaps(session)

    # R-BLANK-EXPLAIN: the stored choice decides the sentence, never the blank printed one
    assert str(gap) == INTENTION_GAP_EXPLAIN.format(name="Demo Auto Finance")
    assert str(gap) != INTENTION_GAP_NONE.format(name="Demo Auto Finance")


@pytest.mark.parametrize(
    "entry",
    [
        {"intention": "surrender"},
        {"intention": "retain_redeem"},
        {"intention": "retain_reaffirm"},
        {"intention": "retain_explain", "explain": "I keep paying as agreed."},
        # words kept under another choice ask for nothing (4e-R16)
        {"intention": "surrender", "explain": "Words from an earlier choice."},
    ],
)
def test_a_chosen_row_has_no_gap(session, entry):
    debt = _secured(session)
    lease = _lease(session)
    for assumed in ("yes", "no"):
        answer_intentions(
            session, secured={str(debt.pk): entry}, leases={str(lease.pk): {"assumed": assumed}}
        )

        assert intention_step_gaps(session) == []


def test_an_undecided_lease_says_its_answer_is_open(session):
    lease = _lease(session, name="Demo Leasing")
    answer_intentions(session, leases={str(lease.pk): {"assumed": "undecided"}})

    assert [str(g) for g in intention_step_gaps(session)] == [
        LEASE_GAP_UNDECIDED.format(name="Demo Leasing")
    ]


def test_a_nameless_row_is_called_one_amount_owed_or_one_contract(session):
    _secured(session, name="   ")
    _lease(session, name="")

    assert [str(g) for g in intention_step_gaps(session)] == [
        INTENTION_GAP_NONE.format(name="one amount owed"),
        LEASE_GAP_NONE.format(name="one contract"),
    ]


def test_a_residential_lease_and_an_unsecured_debt_ask_for_no_choice(session):
    _lease(session, kind="residential")
    complete_debt(session)

    assert intention_step_gaps(session) == []


# ── Never a gate ─────────────────────────────────────────────────────────


def test_too_long_and_open_choices_never_hold_complete(filer, session):
    client, _ = filer
    open_debt = _secured(session, name="Demo Auto Finance")
    undecided = _secured(session, name="Demo Credit Union")
    blank_words = _secured(session, name="Demo Motor Credit")
    explained = _secured(session, name=WIDE_NAME)  # too long for Schedule D's box
    leased_car = _vehicle(session, description="Demo leased car")
    linked_lease(
        session, leased_car, "250", counterparty_name="Demo Leasing", description="WWWW " * 37
    )
    linked_lease(
        session,
        _vehicle(session, description="Demo second car"),
        "200",
        counterparty_name="Demo Second Leasing",
        description="Demo second car lease",
    )
    lease_ids = [c.pk for c in session.executory_contracts.order_by("pk")]
    answer_intentions(
        session,
        secured={
            str(undecided.pk): {"intention": "undecided"},
            str(blank_words.pk): {"intention": "retain_explain", "explain": "  "},
            str(explained.pk): {"intention": "retain_explain", "explain": "a " + "W" * 31},
        },
        leases={str(lease_ids[1]): {"assumed": "undecided"}},
    )
    answer_household(session, asset_lines=["3"], claims={"contracts_answer": "yes"})
    finish_intake(session)
    listed = completion_gaps(session)
    # Every kind of new detail stands: each open choice, and a too-long text on each step
    new = {
        INTENTION_GAP_NONE.format(name=open_debt.creditor_name),
        INTENTION_GAP_UNDECIDED.format(name="Demo Credit Union"),
        INTENTION_GAP_EXPLAIN.format(name="Demo Motor Credit"),
        LEASE_GAP_NONE.format(name="Demo Leasing"),
        LEASE_GAP_UNDECIDED.format(name="Demo Second Leasing"),
        _too_long("creditor_name", "schedule_d"),
        _too_long("description", "form_108"),
        _too_long("explain", "form_108"),
    }
    assert new <= {str(g) for g in listed}
    assert {g.kind for g in listed if str(g) in new} == {Gap.DETAIL}

    response = client.post(f"/api/intake/sessions/{session.pk}/complete/")

    assert response.status_code == 200, response.data
    session.refresh_from_db()
    assert session.status == "completed"


# ── The too-long texts (4e-R4, 4e-R5) ────────────────────────────────────


def _wide_name(session):
    assert _refuses("schedule_d", {"Creditors Name": WIDE_NAME})
    assert not _refuses("form_108", {"Creditors Name 1a": WIDE_NAME})
    debt = _secured(session, name=WIDE_NAME)
    return "debts", _too_long("creditor_name", "schedule_d"), ("schedule_d",), debt


def _fifth_rows_collateral(session):
    assert not _refuses(
        "schedule_d", {"As of the date you file the claim is Check all that apply_5": SHEET_WORD}
    )
    assert not _refuses("form_108", {"PropertyDescription 1a": SHEET_WORD})
    for n in range(4):
        _secured(session, name=f"Demo Lender {n}")
    debt = _secured(session, name="Demo Lender 9", description=SHEET_WORD)
    return "debts", _too_long("collateral_description", "form_108"), ("form_108",), debt


def _lease_description(session):
    description = "WWWW " * 37
    assert _refuses("form_108", {"PropertyDescription 2a": description})
    assert not _refuses("schedule_g", {"Contact Info 2.1": description})
    lease = _lease(session, description=description)
    return "contracts", _too_long("description", "form_108"), ("form_108",), lease


@pytest.mark.parametrize(
    "build",
    [_wide_name, _fifth_rows_collateral, _lease_description],
    ids=["schedule-d-name", "fifth-row-collateral-on-the-sheet", "lease-description"],
)
def test_every_text_generate_refuses_as_too_long_is_listed(session, build):
    step, sentence, forms, _ = build(session)

    gaps = _text_gaps(session, step)

    assert [(str(g), g.kind, g.forms) for g in gaps] == [(sentence, Gap.DETAIL, forms)]


def test_the_fifth_rows_collateral_is_not_listed_on_row_one(session):
    # The control for the sheet case: the same word on a row Form 108's own box prints fits.
    _secured(session, name="Demo Lender", description=SHEET_WORD)

    assert _text_gaps(session, "debts") == []


def test_a_text_over_its_cap_is_listed_with_the_caps_form(session):
    name = "i" * 50  # over Schedule D's cap of 43, the smallest of a secured row's name boxes
    assert not _refuses("schedule_d", {"Creditors Name": name})
    assert not _refuses("form_108", {"Creditors Name 1a": name})
    _secured(session, name=name)

    gaps = _text_gaps(session, "debts")

    assert [(str(g), g.forms) for g in gaps] == [
        (_too_long("creditor_name", "schedule_d"), ("schedule_d",))
    ]


def test_a_text_that_fits_everywhere_is_not_listed(session):
    debt = _secured(session, name="Demo Auto Finance", description="2019 Demo sedan")
    _choose(session, debt, intention="retain_explain", explain="I keep paying as agreed.")
    _lease(session, name="Demo Leasing", description="Demo car lease")
    _lease(session, name="Demo Property Management", kind="residential")
    complete_debt(session, creditor_name="Demo Card Services")

    assert claim_text_gaps(session) == []


def test_a_letter_the_form_cant_print_is_not_called_too_long(session):
    name = "Demo □ Bank"  # the template's /.notdef: no box prints it
    with pytest.raises(UnprintableLetter):
        PDFFormFiller().check("schedule_d", {"Creditors Name": name})
    debt = _secured(session, name=name)

    assert _text_gaps(session, "debts") == []
    assert ("debt", debt.pk, "creditor_name") not in too_long_texts(session, CLAIM_TEXT_KEYS)


# ── The explanation (R-EXPLAIN) ──────────────────────────────────────────


def test_an_explanation_whose_break_overflows_explain_2_is_listed(session):
    words = "a " + "W" * 31
    assert len(words) <= intentions.CLAIM_BOX_CAPS["form_108:explain"]
    explain_1, explain_2 = split_explain(words)
    with pytest.raises(ValueTooLong):
        PDFFormFiller().check("form_108", {"Explain1 1a": explain_1, "Explain2 1a": explain_2})
    debt = _secured(session)
    _choose(session, debt, intention="retain_explain", explain=words)

    gaps = _text_gaps(session, "plans")

    assert [(str(g), g.kind, g.forms) for g in gaps] == [
        (_too_long("explain", "form_108"), Gap.DETAIL, ("form_108",))
    ]


def test_a_fifth_rows_explanation_is_measured_on_the_sheet(session):
    words = "W" * 12  # Explain1 can't take it and Explain2 can; the sheet's 96 pt column can't
    explain_1, explain_2 = split_explain(words)
    assert not _refuses("form_108", {"Explain1 1a": explain_1, "Explain2 1a": explain_2})
    debts = [_secured(session, name=f"Demo Lender {n}") for n in range(5)]
    answer_intentions(
        session,
        secured={str(d.pk): {"intention": "retain_explain", "explain": words} for d in debts},
    )

    gaps = _text_gaps(session, "plans")

    # only the fifth row, which prints on the sheet, is refused
    assert [str(g) for g in gaps] == [_too_long("explain", "form_108")]
    refused = too_long_texts(session, ["explain"])
    assert set(refused) == {("debt", debts[4].pk, "explain")}


def test_an_explanation_over_its_cap_that_fits_is_listed_by_length(session):
    words = "i " * 35
    assert len(words) > intentions.CLAIM_BOX_CAPS["form_108:explain"]
    explain_1, explain_2 = split_explain(words.strip())
    assert not _refuses("form_108", {"Explain1 1a": explain_1, "Explain2 1a": explain_2})
    debt = _secured(session)
    _choose(session, debt, intention="retain_explain", explain=words)

    assert [str(g) for g in _text_gaps(session, "plans")] == [_too_long("explain", "form_108")]


def test_words_that_reach_the_cap_only_through_spaces_are_not_listed(session):
    # T5-R1: Explain1 and Explain2 print the trimmed words (F6), and the browser's note counts them
    # trimmed, so spaces around them never make a detail
    words = "   I keep paying as agreed." + " " * 50
    cap = intentions.CLAIM_BOX_CAPS["form_108:explain"]
    assert len(words) > cap >= len(words.strip())
    explain_1, explain_2 = split_explain(words.strip())
    assert not _refuses("form_108", {"Explain1 1a": explain_1, "Explain2 1a": explain_2})
    debt = _secured(session)
    _choose(session, debt, intention="retain_explain", explain=words)

    assert _text_gaps(session, "plans") == []


@pytest.mark.parametrize(
    "intention", ["surrender", "retain_redeem", "retain_reaffirm", "undecided"]
)
def test_words_kept_under_another_choice_are_never_measured(session, intention):
    debt = _secured(session)
    _choose(session, debt, intention=intention, explain="W" * 80)

    assert _text_gaps(session, "plans") == []


# ── Each row on its own forms ────────────────────────────────────────────


def test_an_unsecured_creditors_long_name_never_names_schedule_d_or_form_108(session):
    by_measure = "W" * 45  # E/F Part 2's box refuses a word of 42 W's
    assert _refuses("schedule_e_f", {"Creditors Name_6": by_measure})
    by_length = "i" * 75  # over E/F Part 2's cap of 70, over Schedule D's 43
    assert not _refuses("schedule_e_f", {"Creditors Name_6": by_length})
    complete_debt(session, creditor_name=by_measure)
    complete_debt(session, creditor_name=by_length)

    gaps = _text_gaps(session, "debts")

    assert [(str(g), g.forms) for g in gaps] == [
        (_too_long("creditor_name", "schedule_e_f"), ("schedule_e_f",))
    ] * 2


def test_a_residential_lease_description_is_measured_on_schedule_g_only(session):
    description = "Demo " * 35
    assert len(description) > intentions.CLAIM_BOX_CAPS["form_108:claims.leases[].purpose"]
    assert not _refuses("schedule_g", {"Contact Info 2.1": description})
    _lease(session, kind="residential", description=description)

    assert _text_gaps(session, "contracts") == []

    # The control: the same words on a vehicle lease, which Form 108 prints, are over its cap
    _lease(session, kind="vehicle", description=description)
    assert [str(g) for g in _text_gaps(session, "contracts")] == [
        _too_long("description", "form_108")
    ]


def test_each_rows_cap_is_the_smallest_of_its_own_lists_boxes():
    boxes = json.loads((SCHEMAS / "form_108.limits.json").read_text())["boxes"]
    for (text, list_name), keys in ROW_BOXES.items():
        smallest = min(boxes[key] for key in keys)
        holders = []
        for key in keys:
            form = key.split(":")[0]
            if boxes[key] == smallest and form not in holders:
                holders.append(form)

        assert row_cap(text, list_name) == (smallest, tuple(holders)), (text, list_name)
    # the residential lease is never measured against Form 108, nor an unsecured name against D
    assert row_cap("description", "contracts") == (301, ("schedule_g",))
    assert row_cap("creditor_name", "unsecured") == (70, ("schedule_e_f",))


def test_the_row_list_cases_are_what_the_server_says():
    cases = json.loads(CASES.read_text())
    for case in cases["debts"]:
        assert claim_list_of(SimpleNamespace(**case["debt"])) == case["list"], case["name"]
    for case in cases["contracts"]:
        assert contract_text_list(SimpleNamespace(**case["contract"])) == case["list"], case["name"]
    # every list a row can land in, and the lease list's in and out, are pinned
    assert {c["list"] for c in cases["debts"]} == {"secured", "priority", "unsecured"}
    assert {c["list"] for c in cases["contracts"]} == {"leases", "contracts", None}


def test_the_gaps_endpoint_lists_them_and_writes_nothing(filer, session):
    client, _ = filer
    _secured(session, name=WIDE_NAME)
    _lease(session, name="Demo Leasing")
    before = (session.status, session.current_step, session.completed_at)

    with CaptureQueriesContext(connection) as queries:
        response = client.get(f"/api/intake/sessions/{session.pk}/gaps/")

    assert response.status_code == 200
    listed = [(g["message"], g["step"], g["kind"], g["forms"]) for g in response.data["gaps"]]
    assert (_too_long("creditor_name", "schedule_d"), "debts", "detail", ["schedule_d"]) in listed
    assert (INTENTION_GAP_NONE.format(name=WIDE_NAME), "plans", "detail", ["form_108"]) in listed
    assert (LEASE_GAP_NONE.format(name="Demo Leasing"), "plans", "detail", ["form_108"]) in listed
    writes = [
        q["sql"]
        for q in queries
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        and '"audit_logs"' not in q["sql"]
    ]
    assert writes == []
    session.refresh_from_db()
    assert (session.status, session.current_step, session.completed_at) == before
