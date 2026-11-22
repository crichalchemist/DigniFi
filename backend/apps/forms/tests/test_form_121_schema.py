"""Round-trip tests for Form 121 schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.services.widgets import template_widgets
from apps.intake.models import DebtorInfo, IntakeSession
from apps.intake.tests.builders import answer_petition

User = get_user_model()

# Form 101 (11/26) line 3: the ITIN's last four, one digit a box.
ITIN_LAST_4_ON_101 = ("undefined_7", "undefined_8", "undefined_9", "undefined_10")


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema121", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_ssn(session):
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        middle_name="Marie",
        last_name="Doe",
        ssn="123-45-6789",
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


@pytest.mark.django_db
class TestForm121Schema:
    def test_resolver_produces_output(self, session_with_ssn):
        field_map = resolve(load_schema("form_121"), session_with_ssn)
        assert "Debtor1.First name" in field_map
        assert field_map["Debtor1.First name"] == "Jane"
        assert field_map["Debtor1.Last name"] == "Doe"
        assert "Debtor1a.SSNum" in field_map
        assert field_map["Debtor1a.SSNum"] == "123-45-6789"

    def test_district_name(self, session_with_ssn):
        field_map = resolve(load_schema("form_121"), session_with_ssn)
        assert field_map["Bankruptcy District Information"] == "Northern District of Illinois"

    def test_without_debtor(self, session):
        field_map = resolve(load_schema("form_121"), session)
        assert "Bankruptcy District Information" in field_map

    def test_a_filer_with_a_social_security_number_is_never_marked_as_having_none(
        self, session_with_ssn
    ):
        # Line 2's Debtor 1 box says "You do not have a Social Security number". The old
        # rule would have ticked it for exactly the filers who have one (DIG-68).
        field_map = resolve(load_schema("form_121"), session_with_ssn)
        assert "Check Box1" not in field_map

    def test_a_filer_without_a_social_security_number_is_marked_as_having_none(self, session):
        # Only resolve() reaches this: the packet refuses Form 121 without a 9-digit
        # number (registry._needs_ssn), so a generated packet never ticks the box.
        DebtorInfo.objects.create(
            session=session,
            first_name="Jane",
            middle_name="Marie",
            last_name="Doe",
            ssn="",
            date_of_birth=date(1990, 1, 15),
            phone="312-555-0100",
            email="jane@example.com",
            street_address="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
        )
        field_map = resolve(load_schema("form_121"), session)
        assert field_map.get("Check Box1") == "/On"

    # Form 121 line 3 and line 2's second box read the petition record Form 101 reads (4b-ii,
    # §13.4). Its number boxes are combs: the ITIN box follows a printed 9, so it takes the eight
    # digits after it (PF2-T10-1).

    def test_an_itin_prints_whole_on_form_121_and_only_its_last_four_on_form_101(
        self, session_with_ssn
    ):
        answer_petition(session_with_ssn, itin_answer="yes", itin="900-70-1234")
        on_121 = resolve(load_schema("form_121"), session_with_ssn)
        on_101 = resolve(load_schema("form_101"), session_with_ssn)
        assert on_121["Debtor1a.ITINNum"] == "00-70-1234"
        assert "Check Box3" not in on_121
        assert [on_101.get(box) for box in ITIN_LAST_4_ON_101] == ["1", "2", "3", "4"]

    @pytest.mark.parametrize("answer,ticked", [("no", "/On"), ("yes", None), (None, None)])
    def test_check_box_3_ticks_only_under_an_explicit_no(self, session_with_ssn, answer, ticked):
        # "You do not have an ITIN" is the filer's own No; an unanswered question ticks nothing.
        answer_petition(session_with_ssn, itin_answer=answer)
        assert resolve(load_schema("form_121"), session_with_ssn).get("Check Box3") == ticked

    def test_a_stored_itin_under_a_no_prints_no_number_beside_the_tick(self, session_with_ssn):
        # PF2-T10-2: the number prints only under the Yes, never beside "You do not have an ITIN".
        answer_petition(session_with_ssn, itin_answer="no", itin="900-70-1234")
        field_map = resolve(load_schema("form_121"), session_with_ssn)
        assert field_map.get("Check Box3") == "/On"
        assert "Debtor1a.ITINNum" not in field_map

    @pytest.mark.parametrize("itin", ["90070123", "9007012345", "812-34-5678"])
    def test_a_non_nine_digit_itin_prints_blank_on_both_forms(self, session_with_ssn, itin):
        # Eight or ten digits, or nine not starting with 9 (PF2-U2), is no ITIN: both forms blank.
        answer_petition(session_with_ssn, itin_answer="yes", itin=itin)
        on_121 = resolve(load_schema("form_121"), session_with_ssn)
        on_101 = resolve(load_schema("form_101"), session_with_ssn)
        assert "Debtor1a.ITINNum" not in on_121
        assert [on_101.get(box) for box in ITIN_LAST_4_ON_101] == [None] * 4

    @pytest.mark.parametrize("answer,printed", [("yes", "900-70-4321"), ("no", None)])
    def test_the_other_ssn_prints_on_line_2_only_under_a_yes(
        self, session_with_ssn, answer, printed
    ):
        answer_petition(session_with_ssn, other_ssn_answer=answer, other_ssn="900704321")
        field_map = resolve(load_schema("form_121"), session_with_ssn)
        assert field_map.get("Debtor1b.SSNum") == printed
        # Line 2's first box keeps the filer's own number.
        assert field_map["Debtor1a.SSNum"] == "123-45-6789"

    def test_each_number_fills_its_comb_one_character_a_cell(self, session_with_ssn):
        # A comb box spreads its text one character a cell: a number of the box's /MaxLen puts
        # every dash on the form's printed gap, and check() accepts it.
        answer_petition(
            session_with_ssn,
            itin_answer="yes",
            itin="900701234",
            other_ssn_answer="yes",
            other_ssn="900-70-4321",
        )
        field_map = resolve(load_schema("form_121"), session_with_ssn)
        widgets = {w.full_name: w for w in template_widgets("form_b121.pdf")}
        for box in ("Debtor1a.ITINNum", "Debtor1b.SSNum"):
            assert widgets[box].comb
            assert len(field_map[box]) == widgets[box].max_len, box
        PDFFormFiller().check("form_121", field_map)
