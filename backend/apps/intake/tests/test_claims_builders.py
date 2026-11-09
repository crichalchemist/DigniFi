"""The test builders leave a session that has finished the claim steps (3c3).

Business intent: a forms or Complete test that builds a session through answer_household meets
no claim refusal it didn't ask for, and a test that adds a debt afterwards can still finish.
"""

import re
from decimal import Decimal

import pytest
from django.conf import settings

from apps.districts.models import District
from apps.intake.claims import claim_step_gaps
from apps.intake.models import IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household, complete_debt
from apps.users.models import User

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


@pytest.fixture
def session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    made = IntakeSession.objects.create(user=user, district=district)
    IncomeInfo.objects.create(session=made, monthly_gross_wages=Decimal("3000.00"))
    return IntakeSession.objects.get(pk=made.pk)


def _gaps(session) -> list[str]:
    return [str(gap) for gap in claim_step_gaps(IntakeSession.objects.get(pk=session.pk))]


def _copy_sentence(name: str) -> str:
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    source = (FRONTEND / "constants" / "copy.ts").read_text()
    found = re.search(rf"export const {name} =\s*(['\"])(.*?)\1;", source, re.DOTALL)
    assert found, name
    return found.group(2)


def test_a_session_with_no_debts_has_finished_the_claim_steps_by_default(session):
    answer_household(session)
    assert _gaps(session) == []


def test_claims_none_leaves_the_claim_answers_alone(session):
    answer_household(session, claims=None)
    assert getattr(session, "claim_answers", None) is None
    assert _gaps(session)[0] == _copy_sentence("DEBT_GAP_NO_ANSWER")


def test_a_debt_added_after_answer_household_stays_answerable(session):
    answer_household(session)
    complete_debt(session)
    assert _gaps(session) == []
    assert session.claim_answers.get_answers().get("no_debts") is None


def test_claims_override_the_default_answers(session):
    answer_household(session, claims={"contracts_answer": "yes"})
    assert _gaps(session)[0] == _copy_sentence("CONTRACT_GAP_YES_BUT_NONE")
