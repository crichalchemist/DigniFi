"""
Fitting a value into a template's text box the way pypdf will draw it.

check() (apps.forms.services.pdf_filler) plans each text and combo box with these
functions, without drawing: whether the box's font can print a letter, and the
largest size, from the box's own down to 6 pt, at which the value fits. They mirror
the layout of pypdf 6.13.1's TextStreamAppearance (pypdf/generic/_appearance_stream.py):
the same font, glyph widths, padding, line spacing and clip.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pypdf
from django.conf import settings

# pypdf internal, pinned with pypdf==6.13.1; test_pdf_filler.py fails if it moves.
from pypdf._font import Font

from apps.forms.services.widgets import TemplateWidget

MIN_SIZE = 6.0  # the smallest print a value shrinks to
STEP = 0.5  # the size steps from a box's own size down to MIN_SIZE
_MULTILINE_AUTO_SIZE = 12.0  # where pypdf's auto size starts a multi-line box


@lru_cache(maxsize=64)
def font_for(template_filename: str, font_name: str) -> Font:
    """The font a /DA names, from the template's /AcroForm /DR, as pypdf builds it."""
    reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template_filename)
    return Font.from_font_resource(reader.root_object["/AcroForm"]["/DR"]["/Font"][font_name])


@lru_cache(maxsize=64)
def reverse_cmap_for(template_filename: str, font_name: str) -> dict[str, str]:
    """
    The font's map from each character to the glyph pypdf measures it by, built once:
    pypdf's Font._get_typographic_maps() builds it again on every call (R51).
    """
    reverse_cmap, _ = font_for(template_filename, font_name)._get_typographic_maps()
    return reverse_cmap


def printable(font: Font, letter: str) -> bool:
    """The font's encoding has the letter: pypdf draws it, not "?" or another glyph (R7)."""
    return font.can_encode(letter)


def _escaped(text: str) -> str:
    """The text pypdf lays out: from_text_annotation escapes \\, ( and ) before measuring."""
    return text.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")


def _width(font: Font, reverse_cmap: dict[str, str], text: str, size: float) -> float:
    """The width in points pypdf gives text at size: each character's glyph, then its width."""
    glyphs = "".join(reverse_cmap.get(character, character) for character in _escaped(text))
    return font.get_text_width(glyphs) * size / 1000


def _leading(font: Font) -> float:
    """pypdf's line spacing per point of size, from the font's bounding box."""
    bbox = font.font_descriptor.bbox
    return (bbox[3] - bbox[1]) / 1000


def wrap(
    font: Font, reverse_cmap: dict[str, str], text: str, size: float, width: float
) -> list[str] | None:
    """
    One paragraph broken at spaces into lines no wider than width at size, each line
    taking as many words as fit. Spaces are kept as typed, except one at each break.
    reverse_cmap is the font's, from reverse_cmap_for().

    Returns None when a word is wider than width.
    """
    lines: list[str] = []
    line: str | None = None
    for word in text.split(" "):
        if _width(font, reverse_cmap, word, size) > width:
            return None
        joined = word if line is None else f"{line} {word}"
        if line is None or _width(font, reverse_cmap, joined, size) <= width:
            line = joined
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def _sizes(start: float) -> list[float]:
    """The start, then each 0.5 pt step below it down to MIN_SIZE: [9.3, 9.0, 8.5, …, 6.0]."""
    sizes = [start]
    size = math.floor(start / STEP) * STEP
    if size == start:
        size -= STEP
    while size >= MIN_SIZE:
        sizes.append(size)
        size -= STEP
    return [size for size in sizes if size >= MIN_SIZE]


def fit(widget: TemplateWidget, template_filename: str, text: str) -> tuple[str, float] | None:
    """
    The text as the box will draw it and the size to draw it at: the box's own size,
    or the first 0.5 pt step below it at which the text fits, down to 6 pt. The box's
    font is the one its /DA names in the template.

    A line break starts a new line in a multi-line box and is a space in any other
    box. Returns None when the text fits at no size.
    """
    font = font_for(template_filename, widget.font)
    reverse_cmap = reverse_cmap_for(template_filename, widget.font)
    field_width = widget.width - 4 * widget.margin
    paragraphs = text.splitlines()
    text = "\n".join(paragraphs) if widget.multiline else " ".join(paragraphs)
    if widget.max_len is not None and not widget.comb and len(text) > widget.max_len:
        return None

    if widget.size:
        start = widget.size
    elif widget.multiline:
        start = _MULTILINE_AUTO_SIZE
    else:  # pypdf's auto size: as large as the box's height and width both allow
        at_one_point = _width(font, reverse_cmap, text, 1)
        field_height = widget.height - 2 * widget.margin
        start = round(min(field_height / _leading(font), field_width / (at_one_point or 1)), 1)
    sizes = _sizes(start)

    if widget.comb:
        # Each character has its own cell, so a smaller size can't make room.
        if sizes and (widget.max_len is None or len(_escaped(text)) <= widget.max_len):
            return text, sizes[0]
        return None
    for size in sizes:
        if not widget.multiline:
            if _width(font, reverse_cmap, text, size) <= field_width:
                return text, size
            continue
        wrapped = [
            wrap(font, reverse_cmap, paragraph, size, field_width) for paragraph in paragraphs
        ]
        if None in wrapped:
            continue
        lines = [line for paragraph in wrapped for line in paragraph]
        # Each line takes one line height below line 1, which T3 lowers by 2 × margin so the
        # font's top sits at the clip's top (R35): the last line then stays above its bottom.
        if len(lines) * size * _leading(font) <= widget.height - 2 * widget.margin:
            return "\n".join(lines), size
    return None
