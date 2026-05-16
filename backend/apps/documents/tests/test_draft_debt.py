import pytest

from apps.districts.models import District
from apps.documents.models import DocumentType, UploadedDocument
from apps.documents.services.draft_debt import DraftDebtCreator
from apps.documents.services.processor import ExtractionResult
from apps.intake.models import DebtInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def district(db):
    return District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=338.00,
    )


@pytest.fixture
def session(db, district):
    user = User.objects.create_user(username="drafttest", password="pass")
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def uploaded_doc(db, session):
    user = session.user
    return UploadedDocument.objects.create(
        session=session,
        uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename="bill.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file="documents/2026/05/bill.pdf",
    )


def test_creates_draft_debtinfo(db, session, uploaded_doc):
    result = ExtractionResult(
        fields={
            "creditor_name": "Capital One",
            "account_number": "4111",
            "amount_owed": "1500.00",
            "creditor_type": "credit_card",
        },
        confidence={"overall": 88},
        detected_type=DocumentType.CREDITOR_BILL,
    )
    creator = DraftDebtCreator()
    debt = creator.create_from_result(result, session, uploaded_doc)

    assert debt.is_draft is True
    assert debt.creditor_name == "Capital One"
    assert debt.debt_type == "credit_card"
    assert debt.source_document == uploaded_doc
    assert debt.data_source == "uploaded_document"
    assert DebtInfo.objects.filter(session=session, is_draft=True).count() == 1


def test_unknown_creditor_type_maps_to_other(db, session, uploaded_doc):
    result = ExtractionResult(
        fields={
            "creditor_name": "Unknown Co",
            "amount_owed": "300.00",
            "creditor_type": "payday_loan",
        },
        confidence={"overall": 60},
        detected_type=DocumentType.CREDITOR_BILL,
    )
    creator = DraftDebtCreator()
    debt = creator.create_from_result(result, session, uploaded_doc)
    assert debt.debt_type == "other"


def test_non_creditor_bill_raises(db, session, uploaded_doc):
    result = ExtractionResult(
        fields={"employer_name": "Acme"},
        confidence={"overall": 90},
        detected_type=DocumentType.PAY_STUB,
    )
    creator = DraftDebtCreator()
    with pytest.raises(ValueError, match="CREDITOR_BILL"):
        creator.create_from_result(result, session, uploaded_doc)
