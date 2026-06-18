"""Form 122A-1 Supplement (Chapter 7 Statement of Current Monthly Income Supplement)."""

from typing import Any

from apps.intake.models import IntakeSession


class Form122A1SuppGenerator:
    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> dict[str, Any]:
        return {"form_type": "form_122a1_supp"}

    def preview(self) -> dict[str, Any]:
        return self.generate()

    def pdf_field_map(self) -> dict:
        from apps.forms.schema import load_schema
        from apps.forms.services.fill_resolver import resolve

        schema = load_schema("form_122a1_supp")
        return resolve(schema, self.session)
