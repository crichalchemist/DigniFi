"""
What Form 108 prints from the filer's own choices (forms step 4e, synthetic tier 3).

Business intent: Form 108 is the filer's sworn statement of what they will do with property that
secures a debt and with each personal property lease. It ticks only a box the filer chose, never
one for a choice left open, prints the exempt box only from what Schedule C says, prints each
choice beside its own creditor whatever rows come and go, and never lists a residential lease.
Every session here is synthetic, built through the intake's own models or its API, and every form
is drawn with fill() and read back from the printed page.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.registry import FORM_REGISTRY, build_parts
from apps.forms.services.fill_resolver import resolve_binding
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn, read_sheet_part
from apps.intake.models import DebtorInfo, ExemptionClaim, IncomeInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_exemptions,
    answer_intentions,
    complete_contract,
    complete_debt,
    linked_loan,
    linked_row,
)

User = get_user_model()

# The words the form prints beside each of check1's boxes (the index's option_text).
FORM_WORDS = {
    "surrender": "Surrender the property.",
    "retain_redeem": "Retain the property and redeem it.",
    "retain_reaffirm": "Retain the property and enter into a Reaffirmation Agreement.",
    "retain_explain": "Retain the property and [explain]:",
}
WORDS = "My brother Mateo, the co-owner, keeps paying the loan."


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="form108", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session,
        first_name="Demo",
        middle_name="Q",
        last_name="Filer",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="demo@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(session=session)
    return session


def _secured(session, name, description="Demo car"):
    """A confirmed secured debt on its own vehicle row of Schedule A/B."""
    row = linked_row(session, "3", description=description)
    return linked_loan(session, row, "100", creditor_name=name, collateral_description=description)


def _lease(session, name, kind="vehicle"):
    return complete_contract(
        session, counterparty_name=name, lease_kind=kind, description=f"{name} lease"
    )


def _drawn(session):
    """(widgets by full name, the parts document, the PDF) of the session's drawn Form 108."""
    document = build_parts("form_108", session)
    pdf = PDFFormFiller().fill("form_108", document)
    shown = {}
    for widget in read_drawn("form_108", pdf, document["parts"]):
        shown.setdefault(widget.full_name, []).append(widget)
    return shown, document, pdf


def _ticks(shown, name):
    return {w.state for w in shown[name] if w.state not in ("", "/Off")}


def _text(shown, name):
    (widget,) = shown[name]
    return widget.value


def _sheet(document, group):
    (part,) = [p for p in document["parts"] if p["kind"] == "sheet" and p["group"] == group]
    return part


def _choose(session, debt, entry):
    answer_intentions(session, secured={str(debt.pk): entry} if entry is not None else {})


@pytest.mark.django_db
@pytest.mark.parametrize(
    "entry,state,words",
    [
        ({"intention": "surrender"}, "/surrender", FORM_WORDS["surrender"]),
        ({"intention": "retain_redeem"}, "/retain and redeem", FORM_WORDS["retain_redeem"]),
        (
            {"intention": "retain_reaffirm"},
            "/retain and reaffirmation",
            FORM_WORDS["retain_reaffirm"],
        ),
        (
            {"intention": "retain_explain", "explain": WORDS},
            "/retain and explain",
            FORM_WORDS["retain_explain"],
        ),
        (None, None, ""),
        ({"intention": "undecided"}, None, ""),
        ({"intention": "retain_explain", "explain": "   "}, None, ""),
    ],
    ids=[
        "surrender",
        "retain_redeem",
        "retain_reaffirm",
        "retain_explain",
        "absent",
        "undecided",
        "retain_explain-blank-words",
    ],
)
def test_every_intention_answer_ticks_its_one_box_and_open_ticks_none(session, entry, state, words):
    # Five debts: the first prints on the form's row a and the fifth on Part 1's sheet, each with
    # the same answer, so the box and the sheet's words are judged together.
    first = _secured(session, "Demo A Lender")
    for name in ("Demo B Lender", "Demo C Lender", "Demo D Lender"):
        _secured(session, name)
    fifth = _secured(session, "Demo E Lender")
    secured = {} if entry is None else {str(first.pk): entry, str(fifth.pk): entry}
    answer_intentions(session, secured=secured)

    shown, document, _ = _drawn(session)

    assert _text(shown, "Creditors Name 1a") == "Demo A Lender"
    assert _ticks(shown, "check1 1a") == ({state} if state else set())
    for row in "bcd":
        assert _ticks(shown, f"check1 1{row}") == set()
    (sheet_row,) = _sheet(document, "f108_part_1")["rows"]
    assert sheet_row["line"] == "1.5"
    name, _, intention, explain, _ = sheet_row["cells"]
    assert name == "Demo E Lender"
    assert intention == words
    if state != "/retain and explain":
        # R-BLANK-EXPLAIN: words under no printed retain-and-explain print nowhere.
        assert _text(shown, "Explain1 1a") == ""
        assert _text(shown, "Explain2 1a") == ""
        assert explain == ""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "entry,state",
    [({"assumed": "yes"}, "/yes"), ({"assumed": "no"}, "/no"), ({"assumed": "undecided"}, None)],
    ids=["yes", "no", "undecided"],
)
def test_every_assumed_answer_ticks_its_box_and_open_ticks_none(session, entry, state):
    lease = _lease(session, "Demo Auto Leasing")
    answer_intentions(session, leases={str(lease.pk): entry})

    shown, _, _ = _drawn(session)

    assert _text(shown, "Lessors Name 2a") == "Demo Auto Leasing"
    assert _ticks(shown, "check2a") == ({state} if state else set())


@pytest.mark.django_db
def test_an_unanswered_lease_ticks_neither_box(session):
    _lease(session, "Demo Auto Leasing")

    shown, _, _ = _drawn(session)

    assert _ticks(shown, "check2a") == set()


def _claim(session, row):
    return ExemptionClaim.objects.create(
        session=session, asset=row, other_law="Demo law", amount_kind="fair_market_value"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "state",
    [
        "listed",
        "not_claiming",
        "not_claiming_no_link",
        "later",
        "not_named",
        "no_property",
        "moved",
        "orphaned",
    ],
)
def test_the_exempt_box_follows_schedule_c_and_never_absence(session, state):
    debt = _secured(session, "Demo Lender")
    expected = {"listed": {"/yes"}, "not_claiming": {"/no"}, "not_claiming_no_link": {"/no"}}
    if state == "listed":
        _claim(session, debt.secured_by)
        answer_exemptions(session)
    elif state.startswith("not_claiming"):
        answer_exemptions(session, no_claims=True)
        if state == "not_claiming_no_link":
            debt.secured_by = None
            debt.save()
    elif state == "not_named":
        # Schedule C answered, with a claim on some other property
        _claim(session, linked_row(session, "3", description="Another car"))
        answer_exemptions(session)
    elif state == "no_property":
        debt.secured_by = None
        debt.save()
    elif state == "moved":
        # The claimed property moved to the filer's other intake: no live link, so no Yes
        row = debt.secured_by
        _claim(session, row)
        answer_exemptions(session)
        row.session = IntakeSession.objects.create(user=session.user, district=session.district)
        row.save()
    elif state == "orphaned":
        # A claim whose property is gone never reads as the linked property's claim
        _claim(session, None)
        answer_exemptions(session)

    shown, _, _ = _drawn(session)

    assert _ticks(shown, "check2 1a") == expected.get(state, set())


@pytest.mark.django_db
def test_explain_prints_only_under_retain_explain_and_reads_back_whole(session):
    debt = _secured(session, "Demo Lender")
    typed = f"  {WORDS} "
    _choose(session, debt, {"intention": "retain_explain", "explain": typed})

    shown, _, _ = _drawn(session)

    # The two boxes overlap by 50.5 × 2.7 pt; the readback gives each letter to the box its
    # centre lies in, so the halves are what each box printed.
    halves = [_text(shown, "Explain1 1a"), _text(shown, "Explain2 1a")]
    assert all(halves)
    assert " ".join(halves) == typed.strip()

    _choose(session, debt, {"intention": "retain_reaffirm", "explain": typed})
    shown, _, _ = _drawn(session)

    assert _ticks(shown, "check1 1a") == {"/retain and reaffirmation"}
    assert _text(shown, "Explain1 1a") == ""
    assert _text(shown, "Explain2 1a") == ""


@pytest.mark.django_db
def test_a_choice_stays_with_its_creditor_when_an_earlier_row_is_added_or_removed(session):
    b = _secured(session, "Demo B Lender")
    c = _secured(session, "Demo C Lender")
    _secured(session, "Demo D Lender")
    _choose(session, c, {"intention": "retain_redeem"})

    def where_the_choice_prints():
        shown, _, _ = _drawn(session)
        ticked = [row for row in "abcd" if _ticks(shown, f"check1 1{row}")]
        assert len(ticked) == 1
        (row,) = ticked
        assert _ticks(shown, f"check1 1{row}") == {"/retain and redeem"}
        return row, _text(shown, f"Creditors Name 1{row}")

    assert where_the_choice_prints() == ("b", "Demo C Lender")
    # A debt that sorts first moves every row down one.
    _secured(session, "Demo A Lender")
    assert where_the_choice_prints() == ("c", "Demo C Lender")
    # Removing the debt before it moves it back up; its choice moves with it.
    b.delete()
    assert where_the_choice_prints() == ("b", "Demo C Lender")


@pytest.mark.django_db
def test_a_fifth_secured_debt_and_an_eighth_lease_print_on_the_sheets(session):
    debts = [_secured(session, f"Demo {letter} Lender") for letter in "ABCDE"]
    leases = [_lease(session, f"Demo Leasing {n}") for n in range(1, 9)]
    answer_intentions(
        session,
        secured={str(debts[4].pk): {"intention": "retain_explain", "explain": WORDS}},
        leases={str(leases[7].pk): {"assumed": "yes"}},
    )

    shown, document, pdf = _drawn(session)

    part_1 = _sheet(document, "f108_part_1")
    assert part_1["rows"] == [
        {
            "line": "1.5",
            "cells": ["Demo E Lender", "Demo car", FORM_WORDS["retain_explain"], WORDS, ""],
        }
    ]
    part_2 = _sheet(document, "f108_part_2")
    assert part_2["rows"] == [
        {"line": "2.8", "cells": ["Demo Leasing 8", "Demo Leasing 8 lease", "Yes"]}
    ]
    # Drawn and read back from the printed sheets
    (page,) = read_sheet_part(pdf, part_1)
    assert page.rows == (
        ("1.5", "Demo E Lender", "Demo car", FORM_WORDS["retain_explain"], WORDS, ""),
    )
    (page,) = read_sheet_part(pdf, part_2)
    assert page.rows == (("2.8", "Demo Leasing 8", "Demo Leasing 8 lease", "Yes"),)
    # The form's own rows hold the first four and the first seven
    assert _text(shown, "Creditors Name 1d") == "Demo D Lender"
    assert _text(shown, "Lessors Name 2g") == "Demo Leasing 7"


@pytest.mark.django_db
def test_a_null_kind_lease_is_in_part_2_and_a_residential_one_is_not(session):
    client = APIClient()
    client.force_authenticate(session.user)
    response = client.put(
        f"/api/intake/sessions/{session.pk}/contracts/",
        [
            {
                "counterparty_name": "Demo Kindless Leasing",
                "contract_type": "lease",
                "description": "Demo equipment lease",
            },
            {
                "counterparty_name": "Demo Apartments LLC",
                "contract_type": "lease",
                "lease_kind": "residential",
                "description": "Apartment lease",
            },
        ],
        format="json",
    )
    assert response.status_code == 200, response.content
    # The name is encrypted, so the rows are read in Python, never filtered in SQL.
    kinds = {c.counterparty_name: c.lease_kind for c in session.executory_contracts.all()}
    assert kinds == {"Demo Kindless Leasing": None, "Demo Apartments LLC": "residential"}

    shown, _, _ = _drawn(session)

    assert resolve_binding("claims.leases[].name", session) == ["Demo Kindless Leasing"]
    assert _text(shown, "Lessors Name 2a") == "Demo Kindless Leasing"
    printed = {w.value for widgets in shown.values() for w in widgets}
    assert "Demo Apartments LLC" not in printed


@pytest.mark.django_db
@pytest.mark.parametrize(
    "build,applies",
    [
        (lambda s: None, False),
        (
            lambda s: complete_debt(
                s, is_secured=True, is_draft=True, secured_by=linked_row(s, "3")
            ),
            False,
        ),
        (lambda s: complete_debt(s), False),
        (lambda s: complete_contract(s), False),
        (lambda s: _secured(s, "Demo Lender"), True),
        (lambda s: _lease(s, "Demo Auto Leasing"), True),
    ],
    ids=[
        "nothing",
        "a-draft-only",
        "unsecured-only",
        "residential-lease-only",
        "secured",
        "vehicle-lease",
    ],
)
def test_form_108_applies_to_a_secured_debt_or_an_in_scope_lease_only(session, build, applies):
    build(session)

    assert FORM_REGISTRY["form_108"].applies(session) is applies
