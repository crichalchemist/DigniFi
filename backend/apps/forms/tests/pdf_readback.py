"""Read a filled PDF back widget by widget, the way a viewer sees it."""

from dataclasses import dataclass
from io import BytesIO

import pypdf

from apps.forms.services.pdf_filler import field_of, qualified_name


@dataclass(frozen=True)
class FilledWidget:
    full_name: str
    page: int
    value: str | None  # the field's /V
    state: str | None  # the widget's /AS; what a checkbox shows


def read_widgets(pdf_bytes: bytes) -> list[FilledWidget]:
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    widgets = []
    for page_number, page in enumerate(reader.pages, start=1):
        for annot in page.get("/Annots") or []:
            widget = annot.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            field = field_of(widget)
            value = field.get_inherited("/V")
            state = widget.get("/AS")
            widgets.append(
                FilledWidget(
                    full_name=qualified_name(field),
                    page=page_number,
                    value=None if value is None else str(value),
                    state=None if state is None else str(state),
                )
            )
    return widgets
