"""
Schedules D and E/F: each schedule's question answers from the debts the filer listed, and
its totals print on the lines that ask for them, which 106Sum copies.

Business intent: a trustee reads Schedule D's grand total and E/F's line 6 totals against
the summary (106Sum 2, 3b and 9d copy them), and each schedule's question says whether a
list follows. DigniFi doesn't ask which debts have priority (OQ-3), and deciding it is a
legal judgment, so every unsecured debt counts as nonpriority, and E/F's priority question
and priority totals stay blank (step 2 spec §6.1 B5, Appendix A.10). Line 6f counts only
the unsecured student loans: E/F is the unsecured schedule, and 6i (6j - 6f) must never go
below zero (Ruling T16-a).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.districts.models import District
from apps.forms.registry import build_parts
from apps.forms.schema import load_schema
from apps.forms.services.derivations import DERIVATIONS
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import DebtInfo, DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_household,
    complete_codebtor,
    complete_debt,
    linked_loan,
    linked_row,
)

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemadef", password="pass")
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
        first_name="Jane",
        middle_name="",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    # 106Sum line 8 is CMI, which needs income entered by source.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
    answer_household(session)
    return session


def _debt(session, debt_type, amount, secured=False, priority=False):
    DebtInfo.objects.create(
        session=session,
        creditor_name=f"{debt_type} creditor",
        debt_type=debt_type,
        amount_owed=Decimal(amount),
        is_secured=secured,
        is_priority=priority,
    )


@pytest.fixture
def debts(session):
    # Each debt at its own power of two, so a total that counts the wrong debts can't match.
    _debt(session, "auto_loan", "1000", secured=True)
    _debt(session, "student_loan", "2000", secured=True)
    _debt(session, "student_loan", "4000")
    _debt(session, "credit_card", "8000")
    # Marked priority, but nobody asked the filer (OQ-3): it counts as nonpriority.
    _debt(session, "other", "16000", priority=True)
    return session


def _widgets(session, form_type):
    """What the drawn form prints in each widget."""
    values = resolve(load_schema(form_type), session)
    return read_drawn(form_type, PDFFormFiller().fill(form_type, values))


def _printed(session, form_type):
    """Each box as printed: a text box's value, or the states a checkbox ticks."""
    shown = {}
    for w in _widgets(session, form_type):
        if not w.state:
            shown[w.full_name] = w.value
        elif w.state != "/Off":
            shown.setdefault(w.full_name, set()).add(w.state)
    return shown


def test_schedule_d_prints_its_secured_total_in_the_grand_total_box(debts):
    # Line 2's grand total of Column A is on page 2. The page-3 box asks on which line of
    # Part 1 a creditor was entered, and never gets a dollar amount.
    widgets = _widgets(debts, "schedule_d")

    assert [(w.page, w.value) for w in widgets if w.full_name == "undefined_24"] == [(2, "3000.00")]
    assert [w.value for w in widgets if w.full_name == "undefined_27"] == [""]


@pytest.mark.slow
def test_line_6j_totals_every_unsecured_debt_and_6f_the_unsecured_student_loans(debts):
    shown = _printed(debts, "schedule_e_f")

    assert shown["Total_6f"] == "4000.00"  # the secured student loan is on Schedule D
    assert shown["Total_6i"] == "24000.00"  # the credit card and the debt marked priority
    assert shown["Total_6j"] == "28000.00"


@pytest.mark.slow
def test_a_secured_student_loan_never_turns_line_6i_negative(session):
    # Ruling T16-a: a student loan the filer saved as secured is on Schedule D, not 6f.
    _debt(session, "student_loan", "5000", secured=True)
    _debt(session, "credit_card", "1000")

    shown = _printed(session, "schedule_e_f")

    assert (shown["Total_6f"], shown["Total_6i"], shown["Total_6j"]) == (
        "0.00",
        "1000.00",
        "1000.00",
    )


@pytest.mark.slow
def test_the_summary_copies_the_totals_schedules_d_and_e_f_print(debts):
    d, ef = _printed(debts, "schedule_d"), _printed(debts, "schedule_e_f")
    summary = resolve(load_schema("form_106sum"), debts)

    assert summary["2"] == d["undefined_24"]
    assert summary["3b"] == ef["Total_6j"]
    assert summary["9d"] == ef["Total_6f"]
    # Total liabilities are 2 + 3a + 3b, and 3a stays blank until priority is asked.
    assert Decimal(summary["3c"]) == Decimal(summary["2"]) + Decimal(summary["3b"])


@pytest.mark.slow
@pytest.mark.parametrize(
    "secured,d_ticks,ef_ticks",
    [
        pytest.param(True, {"/yes"}, {"/no"}, id="secured_only"),
        pytest.param(False, {"/no"}, {"/yes"}, id="unsecured_only"),
    ],
)
def test_each_debt_question_answers_yes_only_for_the_debts_its_schedule_lists(
    session, secured, d_ticks, ef_ticks
):
    _debt(session, "auto_loan" if secured else "credit_card", "1000", secured=secured)

    assert _printed(session, "schedule_d").get("check1", set()) == d_ticks
    assert _printed(session, "schedule_e_f").get("check7", set()) == ef_ticks


@pytest.mark.slow
def test_a_filer_with_no_debts_gets_zero_totals_and_no_on_both_questions(session):
    d, ef = _printed(session, "schedule_d"), _printed(session, "schedule_e_f")

    assert d.get("check1", set()) == {"/no"}
    assert ef.get("check7", set()) == {"/no"}
    # Ruling T0-e: the filer finished the intake with no debts listed, so the totals are 0.00.
    assert d["undefined_24"] == "0.00"
    assert (ef["Total_6f"], ef["Total_6i"], ef["Total_6j"]) == ("0.00", "0.00", "0.00")
    assert resolve(load_schema("form_106sum"), session).get("9d") == "0.00"


def _parts_drawn(session, form_type):
    """(the parts, what the drawn form and its copies print), the copies read as their pages."""
    document = build_parts(form_type, session)
    pdf = PDFFormFiller().fill(form_type, document)
    return document["parts"], read_drawn(form_type, pdf, document["parts"])


def _at(drawn, name, copy=None, page=None, tag=None):
    """What one box prints, on the form's own page (copy None) or on a copy."""
    values = [
        w.value
        for w in drawn
        if w.full_name == name
        and w.copy == copy
        and (page is None or w.page == page)
        and (tag is None or w.tag == tag)
    ]
    assert len(values) == 1, (name, copy, values)
    return values[0]


def _ticked(drawn, name, tag=None, copy=None):
    """The states of the boxes of this name (and tag) that print a check mark."""
    return {
        w.state
        for w in drawn
        if w.full_name == name
        and w.copy == copy
        and (tag is None or w.tag == tag)
        and w.state != "/Off"
    }


def _secured(session, **over):
    return complete_debt(
        session,
        **(
            {
                "is_secured": True,
                "creditor_name": "Demo Lender",
                "collateral_description": "Demo property",
                "lien": {"kinds": ["agreement"], "other": ""},
            }
            | over
        ),
    )


def _party(name, **over):
    return {
        "name": name,
        "street_address": "9 Demo Road",
        "street_2": "",
        "city": "Demoville",
        "state": "IL",
        "zip_code": "60601",
        "last_4": "",
    } | over


# Part 1's who-owes widgets by (name, tag), row by row (appendix: row maps).
WHO_DEBTOR_1 = [
    ("check 2", "T21"),
    ("check 3", "T46"),
    ("check 4", "T21"),
    ("check 5", "T51"),
    ("Debtor 1 only_5", "T77"),
]
WHO_ANOTHER = [
    ("check 2", "T26"),
    ("check 3", "T51"),
    ("check 4", "T28"),
    ("check 5", "T56"),
    ("At least one of the debtors and another_5", "T83"),
]


# The other two who-owes widgets of each row: never ticked, whatever the row's answer.
WHO_DEBTOR_2 = [
    ("check 2", "T23"),
    ("check 3", "T48"),
    ("check 4", "T24"),
    ("check 5", "T53"),
    ("Debtor 2 only_5", "T79"),
]
WHO_BOTH = [
    ("check 2", "T24"),
    ("check 3", "T49"),
    ("check 4", "T27"),
    ("check 5", "T54"),
    ("Debtor 1 and Debtor 2 only_5", "T80"),
]


def _who_ticks(drawn, copy=None):
    """Every who-owes widget of every row that prints a check mark, not only DigniFi's two."""
    every = {*WHO_DEBTOR_1, *WHO_ANOTHER, *WHO_DEBTOR_2, *WHO_BOTH}
    return {
        (w.full_name, w.tag)
        for w in drawn
        if (w.full_name, w.tag) in every and w.copy == copy and w.state != "/Off"
    }


def test_a_secured_debt_prints_its_row_with_columns_a_b_and_c(session):
    car = linked_row(session, "3")
    car.set_details({"who": "only_you"})
    car.entire_value = Decimal("14000")
    car.save()
    linked_loan(
        session,
        car,
        Decimal("200"),
        creditor_name="Demo Auto Credit",
        amount_owed=Decimal("8500"),
        street_2="Suite 1",
        collateral_description="2019 Demo sedan",
        claim_status=["disputed"],
        date_incurred="12/2023",
        account_number="55557702",
    )

    _, drawn = _parts_drawn(session, "schedule_d")

    assert _at(drawn, "Creditors Name") == "Demo Auto Credit"
    assert _at(drawn, "Street") == "1 Demo Street"
    assert _at(drawn, "1") == "Suite 1"
    assert (_at(drawn, "2"), _at(drawn, "3"), _at(drawn, "4")) == ("Demoville", "IL", "60601")
    assert (
        _at(drawn, "As of the date you file the claim is Check all that apply") == "2019 Demo sedan"
    )
    assert _at(drawn, "undefined") == "8500.00"
    assert _at(drawn, "undefined_2") == "14000.00"
    assert _at(drawn, "undefined_3") == "0.00"
    assert _at(drawn, "Date debt was incurred") == "12/2023"
    assert _at(drawn, "account number", tag="T32") == "7702"
    assert _ticked(drawn, "An agreement you made such as mortgage or secured") == {"/On"}
    assert _ticked(drawn, "Disputed") == {"/On"}
    assert _ticked(drawn, "Contingent") == set()
    assert _at(drawn, "undefined_9") == "8500.00"
    assert _at(drawn, "undefined_24") == "8500.00"
    assert _at(drawn, "undefined_23") == ""


def test_each_rows_who_owes_box_ticks_alone(session):
    debts = [_secured(session, creditor_name=f"Demo Lender {n}") for n in range(1, 6)]
    _, alone = _parts_drawn(session, "schedule_d")

    assert _who_ticks(alone) == set(WHO_DEBTOR_1)

    complete_codebtor(session, links=[{"kind": "debt", "id": d.pk} for d in debts])
    _, shared = _parts_drawn(session, "schedule_d")

    assert _who_ticks(shared) == set(WHO_ANOTHER)


def test_a_codebtor_on_one_debt_ticks_only_that_rows_another_box(session):
    debts = [_secured(session, creditor_name=f"Demo Lender {n}") for n in range(1, 6)]
    complete_codebtor(session, links=[{"kind": "debt", "id": debts[2].pk}])

    _, drawn = _parts_drawn(session, "schedule_d")

    assert _who_ticks(drawn) == {*WHO_DEBTOR_1[:2], WHO_ANOTHER[2], *WHO_DEBTOR_1[3:]}


def test_a_sixth_secured_debt_continues_on_a_copy_of_page_2(session):
    for n in range(1, 7):
        _secured(session, creditor_name=f"Demo Lender {n}", amount_owed=Decimal("100"))

    parts, drawn = _parts_drawn(session, "schedule_d")

    assert [p["kind"] for p in parts] == ["form", "copy"]
    assert _at(drawn, "Creditors Name_3", copy=1) == "Demo Lender 6"
    assert _at(drawn, "undefined_12", copy=1) == "2.6"
    assert _at(drawn, "undefined_9") == "200.00"
    assert _at(drawn, "undefined_23") == "300.00"
    assert _at(drawn, "undefined_23", copy=1) == "100.00"
    assert _at(drawn, "undefined_24", copy=1) == "600.00"
    assert _at(drawn, "undefined_24") == ""
    assert _at(drawn, "fill_27.0") == "4"
    assert (_at(drawn, "fill_27.1.0"), _at(drawn, "fill_27.1.1")) == ("2", "4")
    assert (_at(drawn, "fill_27.1.0", copy=1), _at(drawn, "fill_27.1.1", copy=1)) == ("3", "4")
    assert (_at(drawn, "fill_28.1.1"), _at(drawn, "fill_28.1.2")) == ("4", "4")


def test_a_fourth_notice_partys_last_4_prints_only_in_its_own_box(session):
    # Part 2 slot 4's last-4 box (`account number@3:T33`) shares its name with Part 1 row 1's
    # (`@1:T32`): the index says it "always mirrors that value", so an untagged binding would
    # print one debt's last 4 in both.
    _secured(session, creditor_name="Demo Lender 1")
    _secured(
        session,
        creditor_name="Demo Lender 2",
        notice_parties=[_party(f"Demo Collections {n}") for n in range(1, 4)]
        + [_party("Demo Collections 4", last_4="4004")],
    )
    _, drawn = _parts_drawn(session, "schedule_d")
    assert _at(drawn, "account number", page=3, tag="T33") == "4004"
    assert _at(drawn, "account number", page=1, tag="T32") == ""


def test_a_first_debts_last_4_stays_out_of_a_fourth_notice_partys_box(session):
    _secured(
        session,
        creditor_name="Demo Lender 1",
        account_number="55557702",
        notice_parties=[_party(f"Demo Collections {n}") for n in range(1, 5)],
    )
    _, drawn = _parts_drawn(session, "schedule_d")
    assert _at(drawn, "account number", page=1, tag="T32") == "7702"
    assert _at(drawn, "account number", page=3, tag="T33") == ""


def test_a_notice_party_prints_on_part_2_with_its_line(session):
    _secured(session, creditor_name="Demo Lender 1")
    _secured(
        session,
        creditor_name="Demo Lender 2",
        notice_parties=[_party("Demo Collections", street_2="Floor 2", last_4="4004")],
    )

    _, drawn = _parts_drawn(session, "schedule_d")

    assert _at(drawn, "Name") == "Demo Collections"
    assert _at(drawn, "Number_6") == "9 Demo Road"
    assert _at(drawn, "Street 1") == "Floor 2"
    assert (_at(drawn, "Street 2"), _at(drawn, "Street 3"), _at(drawn, "Street 4")) == (
        "Demoville",
        "IL",
        "60601",
    )
    assert _at(drawn, "On which line in Part 1 did you enter the creditor") == "2.2"
    assert _at(drawn, "account number 6") == "4004"


def test_a_seventh_notice_party_continues_on_a_copy_of_page_3(session):
    _secured(
        session,
        notice_parties=[_party(f"Demo Collections {n}") for n in range(1, 8)],
    )

    parts, drawn = _parts_drawn(session, "schedule_d")

    assert [(p["kind"], p.get("page")) for p in parts] == [("form", None), ("copy", 3)]
    assert _at(drawn, "Name", copy=1) == "Demo Collections 7"
    assert _at(drawn, "On which line in Part 1 did you enter the creditor", copy=1) == "2.1"


def test_a_household_item_as_collateral_prints_its_value(session):
    # §9.6 synthetic: a line 6 row is no shape that asks who, so the debt's own answer decides.
    item = linked_row(session, "6")
    item.current_value = Decimal("1200")
    item.save()
    linked_loan(
        session, item, Decimal("50"), amount_owed=Decimal("2000"), collateral_who="only_you"
    )

    _, drawn = _parts_drawn(session, "schedule_d")

    assert _at(drawn, "undefined_2") == "1200.00"
    assert _at(drawn, "undefined_3") == "800.00"


def test_two_debts_on_one_property_print_columns_b_and_c_blank(session):
    # C6: the value of a shared property can't be split between its lenders.
    car = linked_row(session, "3")
    car.set_details({"who": "only_you"})
    car.entire_value = Decimal("14000")
    car.save()
    linked_loan(session, car, Decimal("100"), amount_owed=Decimal("5000"))
    linked_loan(session, car, Decimal("100"), amount_owed=Decimal("3000"))

    _, drawn = _parts_drawn(session, "schedule_d")

    assert (_at(drawn, "undefined"), _at(drawn, "undefined_5")) == ("5000.00", "3000.00")
    for box in ("undefined_2", "undefined_3", "undefined_6", "undefined_7"):
        assert _at(drawn, box) == "", box


def test_the_last_page_total_is_the_secured_total(session):
    for amount in ("100.50", "200.25", "300.00"):
        _secured(session, amount_owed=Decimal(amount))

    _, drawn = _parts_drawn(session, "schedule_d")

    assert _at(drawn, "undefined_24") == DERIVATIONS["total_secured_debts"](session)
    assert _at(drawn, "undefined_24") == "600.75"


def test_a_twelfth_secured_debt_prints_2_12_on_the_third_copy(session):
    for n in range(1, 13):
        # Zero-padded: the rows run by name (ordered_debts), so "10" would sort before "2".
        _secured(session, creditor_name=f"Demo Lender {n:02d}")

    parts, drawn = _parts_drawn(session, "schedule_d")

    assert [p["kind"] for p in parts] == ["form", "copy", "copy", "copy"]
    assert _at(drawn, "Creditors Name_3", copy=3) == "Demo Lender 12"
    assert _at(drawn, "Creditors Name_5", copy=3) == ""
    assert _at(drawn, "undefined_12", copy=3) == "2.12"


def _query_count(session):
    with CaptureQueriesContext(connection) as queries:
        build_parts("schedule_d", session)
    return len(queries)


def test_resolving_schedule_d_reads_the_rows_once(session):
    for n in range(3):
        _secured_on_a_car(session, n)
    _query_count(session)  # the first build also fills per-process caches
    few = _query_count(session)
    for n in range(3, 9):
        _secured_on_a_car(session, n)

    assert _query_count(session) == few


def _secured_on_a_car(session, n):
    car = linked_row(session, "3", description=f"Demo car {n}")
    car.set_details({"who": "only_you"})
    car.entire_value = Decimal("9000")
    car.save()
    linked_loan(session, car, Decimal("100"), creditor_name=f"Demo Lender {n}")


def test_lines_the_intake_never_asks_print_nothing(debts):
    # A debt marked priority still leaves E/F's priority question (line 1) and its
    # priority totals (6a-6e) blank (OQ-3); 6g and 6h are never asked.
    shown = _printed(debts, "schedule_e_f")

    assert "check1" not in shown
    for box in ("Total_6a", "Total_6b", "Total_6c", "Total_6d", "Total_6e", "Total_6g", "Total_6h"):
        assert shown[box] == "", box


# Schedule E/F Parts 2 and 3 (3c5 Task 6).


def _unsecured(session, n=1, **over):
    # Zero-padded: the rows run by name (ordered_debts).
    return complete_debt(session, **({"creditor_name": f"Demo Card {n:02d}"} | over))


def test_an_unsecured_debt_prints_its_row(session):
    _unsecured(
        session,
        amount_owed=Decimal("4200"),
        account_number="1001",
        date_incurred="2019–2025",
        street_2="Unit 3",
        offset_answer="no",
        claim_status=[],
    )

    _, drawn = _parts_drawn(session, "schedule_e_f")

    assert _at(drawn, "Creditors Name_6") == "Demo Card 01"
    assert _at(drawn, "account number 6") == "1001"
    assert _at(drawn, "Total_26") == "4200.00"
    assert _at(drawn, "Date debt was incurred_6") == "2019–2025"
    assert _at(drawn, "Street_6") == "1 Demo Street, Unit 3"
    assert (_at(drawn, "City 4.1"), _at(drawn, "State 4.1"), _at(drawn, "Zip 4.1")) == (
        "Demoville",
        "IL",
        "60601",
    )
    assert _ticked(drawn, "check 6") == {"/debtor 1"}
    assert _ticked(drawn, "Other_6")
    assert _ticked(drawn, "check8") == {"/no"}
    assert _at(drawn, "Other unsecurecured claim 4.1") == "Credit card"
    for status in ("Contingent_6", "Unliquidated_6", "Disputed_6"):
        assert _ticked(drawn, status) == set(), status


def test_a_student_loan_ticks_student_loans(session):
    _unsecured(session, debt_type="student_loan")

    _, drawn = _parts_drawn(session, "schedule_e_f")

    assert _ticked(drawn, "Student loans_6")
    assert _ticked(drawn, "Other_6") == set()
    assert _at(drawn, "Other unsecurecured claim 4.1") == ""


def test_a_disputed_debt_with_offset_ticks_both(session):
    _unsecured(session, claim_status=["disputed"], offset_answer="yes")

    _, drawn = _parts_drawn(session, "schedule_e_f")

    assert _ticked(drawn, "Disputed_6")
    assert _ticked(drawn, "check8") == {"/yes"}


def test_a_seventh_unsecured_debt_continues_on_a_copy_of_page_4_numbered_4_7(session):
    for n in range(1, 10):
        _unsecured(session, n)

    parts, drawn = _parts_drawn(session, "schedule_e_f")

    assert [(p["kind"], p.get("page")) for p in parts] == [("form", None), ("copy", 4)]
    assert [_at(drawn, f"Creditors Name_{n}", copy=1) for n in (9, 10, 11)] == [
        "Demo Card 07",
        "Demo Card 08",
        "Demo Card 09",
    ]
    assert [_at(drawn, f"undefined_4.{k}", copy=1) for k in (4, 5, 6)] == ["4.7", "4.8", "4.9"]
    assert _at(drawn, "fill_27.1.8") == "7"
    assert _at(drawn, "fill_27.1.7", page=6) == "7"


def test_part_3_cites_the_line_and_ticks_part_2(session):
    _unsecured(session, 1)
    _unsecured(
        session,
        2,
        notice_parties=[_party("Demo Collections", street_2="Floor 2", last_4="4004")],
    )

    _, drawn = _parts_drawn(session, "schedule_e_f")

    assert _at(drawn, "Creditors Name_12") == "Demo Collections"
    assert _at(drawn, "Street_12") == "9 Demo Road"
    assert _at(drawn, "Street2_12") == "Floor 2"
    assert (_at(drawn, "City 5.1"), _at(drawn, "State 5.1"), _at(drawn, "Zip 5.1")) == (
        "Demoville",
        "IL",
        "60601",
    )
    assert _at(drawn, "Referenced line 5.1") == "4.2"
    assert _at(drawn, "account number 12") == "4004"
    assert _ticked(drawn, "check14") == {"/yes"}


def test_both_groups_overflowing_number_every_page_across_both(session):
    for n in range(1, 8):
        parties = [_party(f"Demo Collections {n}")]
        if n == 1:
            parties.append(_party("Demo Collections 1b"))
        _unsecured(session, n, notice_parties=parties)

    parts, drawn = _parts_drawn(session, "schedule_e_f")

    assert [(p["kind"], p.get("page")) for p in parts] == [
        ("form", None),
        ("copy", 4),
        ("copy", 5),
    ]
    assert _at(drawn, "fill_27.0") == "8"
    assert _at(drawn, "fill_27.1.4") == "4"
    assert _at(drawn, "fill_27.1.4", copy=1) == "5"
    assert (_at(drawn, "fill_27.1.6"), _at(drawn, "fill_27.1.7", page=5)) == ("6", "8")
    # A copy is numbered within its own page's copies, so each page's first copy is copy 1.
    assert _at(drawn, "fill_27.1.6", copy=1) == "7"
    assert (_at(drawn, "fill_27.1.8"), _at(drawn, "fill_27.1.7", page=6)) == ("8", "8")


TOTAL_CLAIM_BOXES = [f"Total_{n}" for n in range(26, 32)]


def test_line_6j_and_6f_add_the_printed_rows(session):
    # 9.5: the totals read the rows the page prints, the copy's included.
    for n in range(1, 9):
        _unsecured(
            session,
            n,
            amount_owed=Decimal(100 * 2**n),
            debt_type="student_loan" if n in (2, 5) else "credit_card",
        )

    _, drawn = _parts_drawn(session, "schedule_e_f")

    printed = [Decimal(w.value) for w in drawn if w.full_name in TOTAL_CLAIM_BOXES and w.value]
    assert len(printed) == 8
    assert sum(printed) == Decimal(_at(drawn, "Total_6j"))
    assert Decimal(_at(drawn, "Total_6f")) == Decimal(100 * 2**2 + 100 * 2**5)


def test_a_creditor_name_too_long_for_its_box_is_refused_with_its_step(session):
    _unsecured(session, creditor_name="W" * 120)

    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_e_f", build_parts("schedule_e_f", session))

    assert refused.value.step == "debts"
    assert refused.value.label == "Part 2: Creditor's name"
    assert "W" not in str(refused.value)
