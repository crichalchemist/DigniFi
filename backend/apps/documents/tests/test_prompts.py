from apps.documents.models import DocumentType
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
