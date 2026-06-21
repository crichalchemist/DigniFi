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


class TestDebtInfoSerializerDraftFields:
    """Verify is_draft and source_document_name appear in serialized output."""

    def _make_session(self):
        user = User.objects.create_user(username="stest", password="pass")
        district = District.objects.create(
            code="ILND3",
            name="Illinois Northern 3",
            state="IL",
            filing_fee_chapter_7=338.00,
        )
        return IntakeSession.objects.create(user=user, district=district)

    def _make_doc(self, session):
        from apps.documents.models import DocumentType, UploadedDocument

        return UploadedDocument.objects.create(
            session=session,
            uploaded_by=session.user,
            document_type=DocumentType.CREDITOR_BILL,
            file="bill.pdf",
            original_filename="Chase_bill.pdf",
            file_size=100,
            mime_type="application/pdf",
        )

    def test_is_draft_included_and_true(self, db):
        from apps.intake.serializers import DebtInfoSerializer

        session = self._make_session()
        doc = self._make_doc(session)
        debt = DebtInfo.objects.create(
            session=session,
            source_document=doc,
            is_draft=True,
            creditor_name="Chase",
            amount_owed="5000.00",
            debt_type="credit_card",
        )
        data = DebtInfoSerializer(debt).data
        assert data["is_draft"] is True

    def test_source_document_name_included(self, db):
        from apps.intake.serializers import DebtInfoSerializer

        session = self._make_session()
        doc = self._make_doc(session)
        debt = DebtInfo.objects.create(
            session=session,
            source_document=doc,
            is_draft=True,
            creditor_name="Chase",
            amount_owed="5000.00",
            debt_type="credit_card",
        )
        data = DebtInfoSerializer(debt).data
        assert data["source_document_name"] == "Chase_bill.pdf"

    def test_source_document_name_none_when_no_document(self, db):
        from apps.intake.serializers import DebtInfoSerializer

        session = self._make_session()
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Manual",
            amount_owed="1000.00",
            debt_type="other",
        )
        data = DebtInfoSerializer(debt).data
        assert data["source_document_name"] is None
