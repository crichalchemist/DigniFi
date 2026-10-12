"""
The verified field index: one row per widget of each AO template.

Built from the templates themselves (see data/forms/field_index/README.md).
Schemas name widgets by an index ``full_name``; apps.forms.checks validates
every schema against it, and the filler and the oracle compare checkbox states
through export_state().
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings

_HEX_ESCAPE = re.compile(r"#([0-9A-Fa-f]{2})")


def export_state(on_state: str) -> str:
    """
    Turn an index ``on_state`` into the PDF export state a filler writes.

    The index stores the raw, #-encoded name with no leading slash
    ("Chapter#207"); pypdf reads the same name as "/Chapter 7".
    """
    return "/" + _HEX_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), on_state)


@dataclass(frozen=True)
class IndexWidget:
    """One widget of a template, as the index records it."""

    full_name: str
    page: int
    type: str  # Text | CheckBox | RadioButton | ComboBox | Button
    on_state: str | None
    basis: str
    label: str
    column: str


def index_path(template_filename: str) -> Path:
    """The index file for a template: <FORM_INDEX_DIRECTORY>/<template stem>.index.json."""
    return Path(settings.FORM_INDEX_DIRECTORY) / f"{Path(template_filename).stem}.index.json"


@lru_cache(maxsize=32)
def load_index(template_filename: str) -> dict[str, tuple[IndexWidget, ...]]:
    """
    Return {full_name: widgets} for a template filename such as "form_b121.pdf".

    A checkbox group has one full name and several widgets, one per option.

    Raises:
        FileNotFoundError: the template has no index file.
    """
    with open(index_path(template_filename)) as f:
        rows = json.load(f)

    widgets: dict[str, list[IndexWidget]] = {}
    for row in rows:
        widgets.setdefault(row["full_name"], []).append(
            IndexWidget(
                full_name=row["full_name"],
                page=row["page"],
                type=row["type"],
                on_state=row["on_state"],
                basis=row["basis"],
                label=row["label"] or "",
                column=row["column"] or "",
            )
        )
    return {name: tuple(ws) for name, ws in widgets.items()}
