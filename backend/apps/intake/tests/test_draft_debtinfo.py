import pytest

from apps.districts.models import District
from apps.intake.models import DebtInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="testuser", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=338.00,
    )
    return IntakeSession.objects.create(user=user, district=district)


def test_debtinfo_has_is_draft_field(db, session):
    debt = DebtInfo.objects.create(
        session=session,
        creditor_name="Test Bank",
        debt_type="credit_card",
        amount_owed="1000.00",
        is_draft=True,
    )
    assert debt.is_draft is True


def test_debtinfo_is_draft_defaults_false(db, session):
    debt = DebtInfo.objects.create(
        session=session,
        creditor_name="Test Bank",
        debt_type="credit_card",
        amount_owed="500.00",
    )
    assert debt.is_draft is False


def test_debtinfo_source_document_nullable(db, session):
    debt = DebtInfo.objects.create(
        session=session,
        creditor_name="Test Bank",
        debt_type="medical",
        amount_owed="200.00",
    )
    assert debt.source_document is None
