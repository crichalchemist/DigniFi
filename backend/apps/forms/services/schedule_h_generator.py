"""Schedule H (Your Codebtors) Generator."""

from typing import Any

from apps.intake.models import IntakeSession


class ScheduleHGenerator:
    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> dict[str, Any]:
        return {"form_type": "schedule_h"}

    def preview(self) -> dict[str, Any]:
        return self.generate()

    def pdf_field_map(self) -> dict:
        from apps.forms.schema import load_schema
        from apps.forms.services.fill_resolver import resolve

        schema = load_schema("schedule_h")
        return resolve(schema, self.session)
