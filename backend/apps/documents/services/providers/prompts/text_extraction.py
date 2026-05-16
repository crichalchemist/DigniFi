from .image_extraction import _DEFAULT_FIELDS, _FIELD_HINTS


def build_text_extraction_prompt(document_type: str, extracted_text: str) -> str:
    fields = _FIELD_HINTS.get(document_type, _DEFAULT_FIELDS)
    return (
        f"You are a document data extraction assistant for a legal filing platform. "
        f'The following text was extracted from a {document_type.replace("_", " ")} document:\n\n'
        f"---\n{extracted_text[:4000]}\n---\n\n"
        f"Extract these fields: {fields}, "
        f"confidence_score (integer 0-100). "
        f"Return ONLY a valid JSON object. Set missing fields to null."
    )
