"""
Fill resolver — turns a FormSchema + IntakeSession into {pdf_field: str}.

Source priority is encoded per-field in the schema (constant/derived/asked/
ingested/signature). This module resolves ``binding`` references; resolve()
(Task 8) orchestrates dispatch, conditional sections, and repeat groups.
"""

from __future__ import annotations

from apps.intake.models import FormAnswer, IntakeSession


def resolve_binding(binding: str, session: IntakeSession) -> str | list[str]:
    """
    Resolve a schema ``binding``:

      - "answer:<form_type>.<key>" → the FormAnswer value, or "" if absent
      - "sofa.<collection>[].<attr>" → list of str over the collection
      - "sofa.<attr>" → scalar str on the SOFAReport
    """
    binding = binding.strip()

    if binding.startswith("answer:"):
        form_type, _, key = binding[len("answer:") :].partition(".")
        ans = FormAnswer.objects.filter(session=session, form_type=form_type, field_key=key).first()
        return ans.value if ans else ""

    if binding.startswith("sofa."):
        path = binding[len("sofa.") :]
        report = getattr(session, "sofa_report", None)
        if "[]." in path:
            coll_name, _, attr = path.partition("[].")
            if report is None:
                return []
            return [str(getattr(row, attr)) for row in getattr(report, coll_name).all()]
        if report is None:
            return ""
        return str(getattr(report, path))

    raise ValueError(f"unrecognized binding: {binding!r}")
