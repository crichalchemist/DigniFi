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


class TestDraftDebtCreatorCreditReport:
    """Tests for multi-tradeline credit report extraction."""

    def test_creates_one_debt_per_nonzero_tradeline(self, db, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Chase Bank",
                    account_number="****1234",
                    amount_owed=Decimal("5000.00"),
                    account_type="credit_card",
                    account_status="open",
                ),
                TradelineItem(
                    creditor_name="Paid Off LLC",
                    account_number=None,
                    amount_owed=Decimal("0"),
                    account_type="other",
                    account_status="closed",
                ),
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)

        assert len(debts) == 1
        assert debts[0].creditor_name == "Chase Bank"
        assert debts[0].is_draft is True
        assert debts[0].source_document == uploaded_doc
        assert debts[0].session == session

    def test_skips_zero_balance_tradelines(self, db, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Zero Balance",
                    account_number=None,
                    amount_owed=Decimal("0"),
                    account_type="credit_card",
                    account_status="closed",
                )
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts == []

    def test_empty_tradelines_returns_empty_list(self, db, session, uploaded_doc):
        from apps.documents.schemas.credit_report import CreditReportExtraction

        result = CreditReportExtraction(tradelines=[])
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts == []

    def test_maps_account_type_to_debt_type(self, db, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Auto Dealer",
                    account_number=None,
                    amount_owed=Decimal("12000.00"),
                    account_type="auto_loan",
                    account_status="open",
                )
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts[0].debt_type == "auto_loan"
        assert debts[0].is_secured is True

    def test_accepts_masked_account_numbers(self, db, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Citi",
                    account_number="****9999",
                    amount_owed=Decimal("3500.00"),
                    account_type="credit_card",
                    account_status="open",
                )
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts[0].account_number == "****9999"

    def test_maps_in_collections_status(self, db, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Collections Agency",
                    account_number=None,
                    amount_owed=Decimal("2000.00"),
                    account_type="credit_card",
                    account_status="in_collections",
                )
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts[0].is_in_collections is True

    def test_maps_charged_off_status(self, db, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Charged Off Creditor",
                    account_number=None,
                    amount_owed=Decimal("1500.00"),
                    account_type="credit_card",
                    account_status="charged_off",
                )
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts[0].is_in_collections is True

    def test_normal_status_not_in_collections(self, db, session, uploaded_doc):
        from decimal import Decimal

        from apps.documents.schemas.credit_report import CreditReportExtraction, TradelineItem

        result = CreditReportExtraction(
            tradelines=[
                TradelineItem(
                    creditor_name="Regular Creditor",
                    account_number=None,
                    amount_owed=Decimal("1000.00"),
                    account_type="credit_card",
                    account_status="open",
                )
            ]
        )
        debts = DraftDebtCreator().create_from_credit_report(result, session, uploaded_doc)
        assert debts[0].is_in_collections is False
