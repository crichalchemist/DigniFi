"""One current monthly income (CMI) for the means test, the above-median calculator and the forms.

Business intent: CMI decides who passes the means test, which forms a filer gets and what
122A-1 prints, so all three read the same figure. 11 U.S.C. § 101(10A)(B) leaves Social
Security benefits out of CMI; counting them can push a filer over the median (DIG-49).
A total saved before income was stored by source can't be split by anyone but the filer,
so CMI refuses it in plain words instead of guessing (forms step 2 spec §5.5).
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District, MedianIncome
from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income
from apps.eligibility.services.expense_deduction_calculator import ExpenseDeductionCalculator
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.services.derivations import DERIVATIONS
from apps.intake.models import IncomeInfo, IntakeSession
from apps.users.models import User

SPLIT_BY_SOURCE = "Enter your income by source on the Income step."


@pytest.fixture
def filer(db):
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    MedianIncome.objects.create(
        district=district,
        effective_date=date(2025, 11, 1),
        family_size_1=Decimal("71304.00"),
        family_size_2=Decimal("91526.00"),
        family_size_3=Decimal("110712.00"),
        family_size_4=Decimal("134366.00"),
        family_size_5=Decimal("145466.00"),
        family_size_6=Decimal("156566.00"),
        family_size_7=Decimal("167666.00"),
        family_size_8=Decimal("178766.00"),
        family_size_additional=Decimal("11100.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    return user, session


def test_social_security_never_counts_toward_cmi(filer):
    _, session = filer
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        monthly_gross_wages=Decimal("2000.00"),
        monthly_social_security=Decimal("1500.00"),
        monthly_pension=Decimal("500.00"),
    )

    assert current_monthly_income(session.income_info) == Decimal("2500.00")
    assert MeansTestCalculator(session).calculate()["cmi"] == Decimal("2500.00")
    assert DERIVATIONS["cmi"](session) == "2500.00"
    assert ExpenseDeductionCalculator(session)._get_cmi() == Decimal("2500.00")


def test_a_source_left_empty_counts_as_zero_once_another_is_given(filer):
    _, session = filer
    # A journey types only wages, so the other nine are stored empty.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3200.00"))

    assert current_monthly_income(session.income_info) == Decimal("3200.00")


def test_a_filer_who_typed_zero_income_has_a_cmi_of_zero(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("0.00"))

    assert current_monthly_income(session.income_info) == Decimal("0.00")
    assert MeansTestCalculator(session).calculate()["passes_means_test"] is True


def test_a_filer_living_on_social_security_alone_has_a_cmi_of_zero_not_a_refusal(filer):
    _, session = filer
    # Social Security stays out of the sum, but it is still income the filer gave by source:
    # refusing it would stop an SSDI or SSI filer who did exactly what the Income step asks.
    IncomeInfo.objects.create(session=session, monthly_social_security=Decimal("1400.00"))

    assert current_monthly_income(session.income_info) == Decimal("0.00")
    assert MeansTestCalculator(session).calculate()["passes_means_test"] is True
    assert DERIVATIONS["cmi"](session) == "0.00"
    assert ExpenseDeductionCalculator(session)._get_cmi() == Decimal("0.00")


def test_income_saved_only_as_a_total_is_refused_in_plain_words(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)

    with pytest.raises(IncomeNotSplit) as refused:
        current_monthly_income(session.income_info)

    assert str(refused.value) == SPLIT_BY_SOURCE
    assert isinstance(refused.value, ValueError)


def test_the_means_test_passes_the_refusal_on_without_its_failure_prefix(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)

    with pytest.raises(IncomeNotSplit) as refused:
        MeansTestCalculator(session).calculate()

    assert str(refused.value) == SPLIT_BY_SOURCE


def test_other_means_test_failures_keep_their_prefix(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
    MedianIncome.objects.all().delete()

    with pytest.raises(ValueError, match="^Means test calculation failed: No median income"):
        MeansTestCalculator(session).calculate()


def test_the_above_median_calculator_refuses_income_not_split_instead_of_using_zero(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_income=[9000] * 6)

    with pytest.raises(IncomeNotSplit):
        ExpenseDeductionCalculator(session).calculate()


def test_means_test_endpoint_asks_for_income_by_source_as_a_400(filer):
    user, session = filer
    IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f"/api/intake/sessions/{session.pk}/calculate_means_test/")

    assert response.status_code == 400
    assert response.data["error"] == SPLIT_BY_SOURCE
