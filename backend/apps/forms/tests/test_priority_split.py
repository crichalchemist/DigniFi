"""
Every confirmed unsecured debt prints in exactly one of Schedule E/F's Part 1 and Part 2
(3d spec §6.6).

Business intent: the filer's answer to "does this debt have priority" moves a debt between
two Parts, and the trustee adds each Part up against the summary. A debt in both Parts is
counted twice and a debt in neither is never owed, so the rows and the totals must split the
same debts: Part 1's total plus Part 2's is the confirmed unsecured total, and the summary's
total debts is that plus the secured ones.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.districts.models import District
from apps.forms.services.derivations import DERIVATIONS
from apps.intake.claim_rows import claim_rows
from apps.intake.models import IntakeSession
from apps.intake.tests.builders import complete_debt

User = get_user_model()


def _total(rule, session):
    return Decimal(DERIVATIONS[rule](session))


def _assert_each_debt_prints_in_exactly_one_part(session):
    rows = claim_rows(session)
    in_part_1 = [row.debt.pk for row in rows.priority]
    in_part_2 = [row.debt.pk for row in rows.unsecured]
    unsecured = list(session.debts.confirmed().filter(is_secured=False))

    for debt in unsecured:
        assert (debt.pk in in_part_1) + (debt.pk in in_part_2) == 1, debt.creditor_name
    assert len(in_part_1) + len(in_part_2) == len(unsecured)

    unsecured_total = sum((debt.amount_owed for debt in unsecured), Decimal("0"))
    part_1, part_2 = (
        _total("total_priority_unsecured", session),
        _total("total_nonpriority_unsecured", session),
    )
    assert part_1 + part_2 == unsecured_total
    assert _total("total_debts", session) == (
        _total("total_secured_debts", session) + part_1 + part_2
    )


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="prioritysplit", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def test_each_debt_prints_in_exactly_one_part(session):
    # Each debt at its own power of two, so a total that counts the wrong debts can't match.
    amount = 1
    for answer in ("domestic_support", "taxes", "intoxicated", "other", "no", "not_sure", None):
        complete_debt(
            session,
            creditor_name=f"Demo {answer}",
            amount_owed=Decimal(amount),
            priority_answer=answer,
            past_due_amount=Decimal("0") if answer not in ("no", "not_sure", None) else None,
        )
        amount *= 2
    complete_debt(
        session,
        creditor_name="Demo Lender",
        is_secured=True,
        priority_answer="taxes",
        amount_owed=Decimal(amount),
    )
    complete_debt(
        session,
        creditor_name="Demo Draft",
        is_draft=True,
        priority_answer="taxes",
        amount_owed=Decimal(amount * 2),
    )

    _assert_each_debt_prints_in_exactly_one_part(session)
    assert _total("total_priority_unsecured", session) == Decimal("15")
    assert _total("total_nonpriority_unsecured", session) == Decimal("112")


@pytest.mark.slow
@pytest.mark.django_db
@pytest.mark.parametrize("persona", ["andres", "deshawn", "james", "maria", "priya", "sarah"])
def test_every_persona_splits_its_debts_once(persona):
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", "--reset", persona=persona, verbosity=0)
    session = IntakeSession.objects.filter(user__username=f"demo_{persona}").latest("id")

    _assert_each_debt_prints_in_exactly_one_part(session)
