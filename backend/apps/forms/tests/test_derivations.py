"""Tests for factual derivations and section predicates."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.services.derivations import DERIVATIONS, PREDICATES
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="testuser", password="pw")
    d = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        court_name="x",
        state="IL",
        filing_fee_chapter_7="338.00",
    )
    s = IntakeSession.objects.create(user=user, district=d, status="completed", current_step=6)
    DebtorInfo.objects.create(
        session=s,
        first_name="Maria",
        middle_name="",
        last_name="Torres",
        ssn="000-00-0000",
        date_of_birth=date(1985, 6, 1),
        phone="555-0100",
        email="maria@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
        household_size=3,
    )
    return s


def test_full_name_collapses_blank_middle(session):
    assert DERIVATIONS["full_name"](session) == "Maria Torres"


def test_full_name_includes_middle(session):
    session.debtor_info.middle_name = "A."
    session.debtor_info.save()
    assert DERIVATIONS["full_name"](session) == "Maria A. Torres"


def test_family_size_reads_household_size(session):
    assert DERIVATIONS["family_size"](session) == "3"


def test_chapter_constant(session):
    assert DERIVATIONS["chapter"](session) == "7"


def test_debtor_type_individual(session):
    assert DERIVATIONS["debtor_type"](session) == "Individual"


def test_district_name(session):
    assert DERIVATIONS["district_name"](session) == "Northern District of Illinois"


def test_has_business_predicate_false_without_report(session):
    assert PREDICATES["has_business"](session) is False


def test_has_creditor_payments_predicate_false_without_report(session):
    assert PREDICATES["has_creditor_payments"](session) is False


def test_has_prior_income_predicate_false_without_report(session):
    assert PREDICATES["has_prior_income"](session) is False


@pytest.mark.django_db
def test_has_attorney_predicate():
    from apps.intake.models import FormAnswer

    d = District.objects.create(
        code="ilnd", name="Test", court_name="x", state="IL", filing_fee_chapter_7="1.00"
    )
    user = User.objects.create_user(username="pred_attorney", password="x")
    session = IntakeSession.objects.create(
        district=d, user=user, status="in_progress", current_step=1
    )

    # No FormAnswer yet → defaults to False
    assert PREDICATES["has_attorney"](session) is False

    # With a "yes" answer → True
    FormAnswer.objects.create(
        session=session, form_type="form_107", field_key="attorney_gate", value="yes"
    )
    assert PREDICATES["has_attorney"](session) is True


# ---------------------------------------------------------------------------
# Income rules read the Income step's ten amounts (forms step 2 spec §5.5, §7.7)
# ---------------------------------------------------------------------------

# Each source gets a distinct power of two, so every sum of sources is unique and a rule
# that reads the wrong source, or adds one too many, returns a different figure.
TEN_SOURCES = {
    "monthly_gross_wages": Decimal("1.00"),
    "monthly_overtime": Decimal("2.00"),
    "monthly_tips": Decimal("4.00"),
    "monthly_rental_income": Decimal("8.00"),
    "monthly_pension": Decimal("16.00"),
    "monthly_social_security": Decimal("32.00"),
    "monthly_unemployment": Decimal("64.00"),
    "monthly_child_support": Decimal("128.00"),
    "monthly_alimony": Decimal("256.00"),
    "monthly_other_income": Decimal("512.00"),
}

# The rules switched in 2a commit 4 or created in 2b, with the sources each one adds up
# (spec §6.2's "Returns"). Moved rules keep names that describe their old lines (§6.1).
SWITCHED_RULES = {
    "cmi": [field for field in TEN_SOURCES if field != "monthly_social_security"],
    "schedule_i_net_wages_debtor1": ["monthly_gross_wages", "monthly_tips"],
    "schedule_i_rental_debtor1": ["monthly_rental_income"],
    "schedule_i_child_support_debtor1": ["monthly_child_support", "monthly_alimony"],
    "schedule_i_unemployment_debtor1": ["monthly_unemployment"],
    "schedule_i_social_security_debtor1": ["monthly_social_security"],
    "schedule_i_pension_debtor1": ["monthly_pension"],
    "schedule_i_other_income_debtor1": ["monthly_other_income"],
    "schedule_i_overtime_debtor1": ["monthly_overtime"],
    "schedule_i_gross_income_debtor1": ["monthly_gross_wages", "monthly_tips", "monthly_overtime"],
    "schedule_i_other_income_total_debtor1": [
        "monthly_rental_income",
        "monthly_child_support",
        "monthly_alimony",
        "monthly_unemployment",
        "monthly_social_security",
        "monthly_pension",
        "monthly_other_income",
    ],
    "line1_wages": ["monthly_gross_wages", "monthly_tips", "monthly_overtime"],
    "line6b_child_support_alimony": ["monthly_child_support"],
    "line3_real_property_income": ["monthly_rental_income"],
    "line6a_unemployment": ["monthly_unemployment"],
    "line5a_pension_retirement": ["monthly_pension"],
    "line7_other_income": ["monthly_other_income"],
    "line3_alimony": ["monthly_alimony"],
    # Schedule I line 12 and Schedule J 23a, which copies it: Social Security included (C1)
    "schedule_i_income_total": list(TEN_SOURCES),
    "schedule_j_total_income": list(TEN_SOURCES),
}


@pytest.mark.parametrize("rule,sources", list(SWITCHED_RULES.items()))
def test_each_switched_income_rule_returns_its_own_sources_figure(session, rule, sources):
    IncomeInfo.objects.create(session=session, **TEN_SOURCES)

    expected = sum((TEN_SOURCES[field] for field in sources), Decimal("0"))
    assert DERIVATIONS[rule](session) == f"{expected:.2f}"


@pytest.mark.parametrize("rule", [rule for rule in SWITCHED_RULES if rule != "cmi"])
def test_an_income_rule_prints_blank_when_the_filer_gave_none_of_its_sources(session, rule):
    # Every other source was given, so the rule must not borrow one of them.
    given = {f: a for f, a in TEN_SOURCES.items() if f not in SWITCHED_RULES[rule]}
    IncomeInfo.objects.create(session=session, **given)

    assert DERIVATIONS[rule](session) == ""


@pytest.mark.parametrize("rule", [rule for rule in SWITCHED_RULES if rule != "cmi"])
def test_an_income_source_typed_as_zero_prints_zero(session, rule):
    IncomeInfo.objects.create(session=session, **{field: Decimal("0") for field in TEN_SOURCES})

    assert DERIVATIONS[rule](session) == "0.00"


def test_an_income_sum_counts_an_empty_source_as_zero(session):
    # Alimony given, child support left empty: Schedule I's support line still prints.
    IncomeInfo.objects.create(session=session, monthly_alimony=Decimal("300.00"))

    assert DERIVATIONS["schedule_i_child_support_debtor1"](session) == "300.00"


@pytest.mark.parametrize(
    "other_income,named",
    [(Decimal("0.01"), "Other income"), (Decimal("0"), ""), (None, "")],
)
def test_other_income_is_named_only_when_the_filer_has_some(session, other_income, named):
    # 122A-1 line 10 and Schedule I 8h ask what the other income is (Appendix E 5).
    IncomeInfo.objects.create(
        session=session, monthly_gross_wages=Decimal("100.00"), monthly_other_income=other_income
    )

    assert DERIVATIONS["other_income_label"](session) == named


def test_other_income_is_not_named_before_the_filer_gives_any_income(session):
    assert DERIVATIONS["other_income_label"](session) == ""


def test_cmi_refuses_a_session_with_no_income_by_source(session):
    from apps.eligibility.cmi import IncomeNotSplit

    with pytest.raises(IncomeNotSplit):
        DERIVATIONS["cmi"](session)
    IncomeInfo.objects.create(session=session, monthly_income=[2500] * 6)
    with pytest.raises(IncomeNotSplit):
        DERIVATIONS["cmi"](session)
