"""The List of Creditors' entries (3c6 spec §10.3, rulings R5 and R6).

Business intent: the court's list holds every name and address the schedules print, once each,
with the step of the row it came from, and nothing the filer can no longer see.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.districts.models import District
from apps.forms.services.fill_resolver import (
    CLAIM_CELLS,
    creditor_entries,
    resolve_binding,
    row_fixes,
)
from apps.intake.claim_rows import claim_rows
from apps.intake.models import DebtorInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_claims,
    complete_codebtor,
    complete_contract,
    complete_debt,
    linked_loan,
    linked_row,
)
from apps.users.models import User

ENTRY = "claims.creditor_list[].entry"


@pytest.fixture
def filer(db):
    District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return User.objects.create_user(username="filer", password="pw")


@pytest.fixture
def session(filer):
    return IntakeSession.objects.create(user=filer, district=District.objects.get(code="ILND"))


def _fresh(session):
    return IntakeSession.objects.get(pk=session.pk)


def _entries(session):
    return creditor_entries(claim_rows(_fresh(session)))


def _party(name, street="9 Demo Street", **over):
    return {
        "name": name,
        "street_address": street,
        "street_2": "",
        "city": "Demoville",
        "state": "IL",
        "zip_code": "60601",
        "outside_us": False,
        "last_4": "",
    } | over


def _names(entries):
    return [e.text.split("\n")[0] for e in entries]


def test_entries_follow_the_schedules_in_print_order(session):
    complete_debt(session, creditor_name="Unsecured Card", notice_parties=[_party("Unsec Notice")])
    linked_loan(
        session,
        linked_row(session, "3"),
        "100",
        creditor_name="Secured Auto",
        notice_parties=[_party("Sec Notice")],
    )
    complete_debt(
        session,
        creditor_name="Zeta Tax",
        priority_answer="taxes",
        past_due_amount=Decimal("0.00"),
        notice_parties=[_party("Tax Notice", street="7 Demo Street")],
    )
    complete_contract(session, counterparty_name="Lease Co")
    complete_codebtor(session, links=[], name="Co Signer")
    entries = _entries(session)
    assert [(n, e.step) for n, e in zip(_names(entries), entries, strict=True)] == [
        ("Secured Auto", "debts"),
        ("Sec Notice", "debts"),
        ("Zeta Tax", "debts"),
        ("Unsecured Card", "debts"),
        ("Tax Notice", "debts"),
        ("Unsec Notice", "debts"),
        ("Lease Co", "contracts"),
        ("Co Signer", "codebtors"),
    ]


def test_a_creditor_in_both_parts_prints_once_at_its_part_1_row(session):
    complete_debt(
        session,
        creditor_name="Demo Revenue",
        priority_answer="taxes",
        past_due_amount=Decimal("0.00"),
    )
    complete_debt(session, creditor_name="Demo Revenue", priority_answer="no")
    complete_debt(
        session,
        creditor_name="Aaron Card",
        priority_answer="no",
        street_address="3 Other Way",
    )
    assert _names(_entries(session)) == ["Demo Revenue", "Aaron Card"]


def test_a_name_and_address_entered_twice_prints_once(session):
    first = complete_debt(session, creditor_name="Demo Card Services")
    complete_debt(session, creditor_name="Other Card", notice_parties=[_party("Shared Notice")])
    complete_debt(session, creditor_name="Third Card", notice_parties=[_party("Shared Notice")])
    u = [
        complete_debt(session, creditor_name=f"Line {i}", street_address=f"{i} Demo Way")
        for i in range(3)
    ]
    # a codebtor with a creditor's name and address
    complete_codebtor(session, links=[], name="Demo Card Services")
    # a codebtor linked to three E/F lines: two H rows
    complete_codebtor(
        session,
        links=[{"kind": "debt", "id": d.pk} for d in u],
        name="Linked Person",
        street_address="5 Linked Lane",
    )
    rows = claim_rows(_fresh(session))
    assert [r.codebtor.name for r in rows.codebtors].count("Linked Person") == 2
    assert [r.codebtor.name for r in rows.codebtors].count("Demo Card Services") == 1
    assert first.pk
    entries = _entries(session)
    names = _names(entries)
    assert names.count("Demo Card Services") == 1
    assert names.count("Shared Notice") == 1
    assert names.count("Linked Person") == 1
    by_name = dict(zip(names, entries, strict=True))
    assert by_name["Demo Card Services"].step == "debts"
    assert by_name["Linked Person"].step == "codebtors"


def test_case_and_spacing_do_not_make_a_new_entry(session):
    complete_debt(session, creditor_name="Demo  Card  Services", street_address="1 Demo Way")
    complete_debt(session, creditor_name="demo card services", street_address="1 demo way ")
    entries = _entries(session)
    assert len(entries) == 1
    assert entries[0].text.startswith("Demo  Card  Services\n1 Demo Way\n")


def test_accents_make_a_different_entry_but_how_a_letter_was_typed_does_not(session):
    complete_debt(session, creditor_name="José Demo", street_address="1 Demo Way")
    complete_debt(session, creditor_name="Jose Demo", street_address="1 Demo Way")
    assert len(_entries(session)) == 2

    composed = "José Other"
    decomposed = "José Other"
    complete_debt(session, creditor_name=composed, street_address="2 Demo Way")
    complete_debt(session, creditor_name=decomposed, street_address="2 Demo Way")
    others = [e for e in _entries(session) if "Other" in e.text]
    assert len(others) == 1
    assert others[0].text.startswith(composed + "\n")


def test_a_different_address_is_a_different_entry(session):
    complete_debt(session, creditor_name="Demo Card Services", street_address="1 Demo Way")
    complete_debt(session, creditor_name="Demo Card Services", street_address="2 Demo Way")
    assert len(_entries(session)) == 2


@pytest.mark.parametrize(
    ("part", "other"),
    [
        ("street_2", "Suite 9"),
        ("city", "Otherville"),
        ("state", "WI"),
        ("zip_code", "53201"),
    ],
)
def test_the_same_name_and_street_elsewhere_is_a_different_entry(session, part, other):
    # A creditor with one name and street in two cities, or two suites, is two mailings.
    complete_debt(session, creditor_name="Demo Card Services", street_address="1 Demo Way")
    complete_debt(
        session, creditor_name="Demo Card Services", street_address="1 Demo Way", **{part: other}
    )
    assert len(_entries(session)) == 2


def test_an_entry_never_shows_a_creditors_name_in_its_repr(session):
    # Global Constraint: no logger call or __str__ may carry a creditor's name or address.
    complete_debt(session, creditor_name="Distinctive Creditor", street_address="77 Secret Way")
    (entry,) = _entries(session)
    for shown in (repr(entry), str(entry)):
        assert "Distinctive" not in shown
        assert "Secret" not in shown
        assert "debts" in shown


def test_an_entry_prints_name_street_and_city_state_zip_on_their_own_lines(session):
    complete_debt(session, street_2="Suite 4", city="Chicago")
    complete_debt(session, creditor_name="Plain Bank", street_address="2 Demo Way", city="Chicago")
    texts = {_names([e])[0]: e.text for e in _entries(session)}
    assert (
        texts["Demo Card Services"]
        == "Demo Card Services\n1 Demo Street\nSuite 4\nChicago, IL 60601"
    )
    assert texts["Plain Bank"] == "Plain Bank\n2 Demo Way\nChicago, IL 60601"


def test_a_blank_part_of_the_city_line_leaves_no_stray_comma_or_space(session):
    complete_debt(session, creditor_name="A", state="", zip_code="60601")
    complete_debt(session, creditor_name="B", state="IL", zip_code="")
    complete_debt(session, creditor_name="C", city="", state="", zip_code="")
    texts = {_names([e])[0]: e.text.split("\n")[-1] for e in _entries(session)}
    assert texts == {"A": "Demoville 60601", "B": "Demoville, IL", "C": "1 Demo Street"}


def test_an_address_outside_the_us_prints_the_city_alone(session):
    complete_debt(
        session,
        creditor_name="Foreign Bank",
        outside_us=True,
        city="Toronto, Canada",
        state="ON",
        zip_code="M5V 2T6",
    )
    (entry,) = _entries(session)
    assert entry.text.split("\n")[-1] == "Toronto, Canada"
    assert "ON" not in entry.text.split("\n")[-1]
    assert "M5V" not in entry.text


def test_a_draft_debt_is_not_on_the_list(session):
    complete_debt(session, creditor_name="Draft Card", is_draft=True, notice_parties=[_party("DN")])
    complete_debt(session, creditor_name="Confirmed Card", street_address="7 Demo Way")
    assert _names(_entries(session)) == ["Confirmed Card"]


def test_h_line_2_spouse_is_not_on_the_list(session):
    answer_claims(
        session,
        community_lived="yes",
        community_spouse_lived_with="yes",
        community_state="Illinois",
        community_spouse_name="Spouse Person",
        community_spouse_street_address="3 Spouse Street",
        community_spouse_city="Demoville",
        community_spouse_state="IL",
        community_spouse_zip_code="60601",
    )
    complete_debt(session, creditor_name="Only Creditor", street_address="8 Demo Way")
    assert _names(_entries(session)) == ["Only Creditor"]


def test_the_filer_is_never_added_and_a_namesake_creditor_stays(session):
    assert _entries(session) == []
    DebtorInfo.objects.create(
        session=session,
        first_name="Jo",
        last_name="Demo",
        ssn="900-11-0001",
        date_of_birth=date(1988, 6, 15),
    )
    complete_debt(session, creditor_name="Jo Demo")
    assert _names(_entries(session)) == ["Jo Demo"]


def test_the_slots_binding_reads_the_entries_and_their_steps(session):
    complete_debt(session, creditor_name="Card One")
    complete_contract(session, counterparty_name="Lease Co")
    complete_codebtor(session, links=[], name="Co Signer")
    live = _fresh(session)
    with_rows = resolve_binding(ENTRY, live)
    fixes = row_fixes(ENTRY, live)
    assert [t.split("\n")[0] for t in with_rows] == ["Card One", "Lease Co", "Co Signer"]
    assert fixes == [{"step": "debts"}, {"step": "contracts"}, {"step": "codebtors"}]
    assert len(fixes) == len(with_rows)
    assert row_fixes("claims.contracts[].name", live) is None


def test_the_entry_cell_is_the_entry_text():
    assert CLAIM_CELLS["creditor_list"]["entry"](type("E", (), {"text": "x"})()) == "x"
