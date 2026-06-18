"""Form 122B (Chapter 7 Means Test Calculation - Alternative)."""

from typing import Any

from apps.intake.models import IntakeSession


class Form122BGenerator:
    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> dict[str, Any]:
        return {"form_type": "form_122b"}

    def preview(self) -> dict[str, Any]:
        return self.generate()

    def pdf_field_map(self) -> dict:
        from apps.forms.schema import load_schema
        from apps.forms.services.fill_resolver import resolve

        schema = load_schema("form_122b")
        return resolve(schema, self.session)
