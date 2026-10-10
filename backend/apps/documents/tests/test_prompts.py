import pytest

from apps.documents.models import DocumentType
from apps.documents.schemas.credit_report import TradelineItem
from apps.documents.services.providers.prompts.image_extraction import build_image_extraction_prompt
from apps.documents.services.providers.prompts.text_extraction import build_text_extraction_prompt


def test_image_prompt_contains_doc_type():
    prompt = build_image_extraction_prompt(DocumentType.CREDITOR_BILL)
    assert "creditor" in prompt.lower()
    assert "JSON" in prompt


def test_image_prompt_contains_schema_fields():
    prompt = build_image_extraction_prompt(DocumentType.CREDITOR_BILL)
    assert "creditor_name" in prompt
    assert "amount_owed" in prompt


def test_text_prompt_embeds_content():
    prompt = build_text_extraction_prompt(DocumentType.PAY_STUB, "Employer: Acme\nGross: $3200")
    assert "Acme" in prompt
    assert "gross_pay" in prompt


def test_text_prompt_requests_json():
    prompt = build_text_extraction_prompt(DocumentType.CREDITOR_BILL, "Capital One $450")
    assert "JSON" in prompt
    assert "confidence_score" in prompt


@pytest.mark.parametrize(
    "build_prompt",
    [
        build_image_extraction_prompt,
        lambda doc_type: build_text_extraction_prompt(doc_type, "EQUIFAX CREDIT FILE ..."),
    ],
    ids=["scanned", "text-layer"],
)
def test_credit_report_prompt_asks_for_every_field_the_importer_needs(build_prompt):
    """Without the hint the model is asked for "all visible fields" and never returns
    tradelines, so no account on a credit report reaches the Amounts Owed step."""
    prompt = build_prompt(DocumentType.CREDIT_REPORT)

    assert "tradelines" in prompt
    for field in TradelineItem.model_fields:
        assert field in prompt
    # DraftDebtCreator marks a debt secured or in collections only on these exact values.
    for value in ("auto_loan", "mortgage", "in_collections", "charged_off"):
        assert value in prompt
