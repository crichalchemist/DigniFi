"""Form 122A-2 (Chapter 7 Means Test Calculation) Generator."""

from typing import Any

from apps.intake.models import IntakeSession


class Form122A2Generator:
    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> dict[str, Any]:
        return {"form_type": "form_122a2"}

    def preview(self) -> dict[str, Any]:
        return self.generate()

    def pdf_field_map(self) -> dict:
        from apps.forms.schema import load_schema
        from apps.forms.services.fill_resolver import resolve

        schema = load_schema("form_122a2")
        return resolve(schema, self.session)
