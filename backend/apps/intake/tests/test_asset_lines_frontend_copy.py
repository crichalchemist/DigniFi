"""
The Assets step's catalog is typed twice, once in the server (LINES) and once in the wizard's
constants, and the server drops an unknown `details` key silently. A line, kind or key spelled
differently on one side would ask the filer one thing and print another, or lose an answer with
no error, so this pins the two sides to each other (3b spec §5).
"""

import re

import pytest
from django.conf import settings
from rest_framework import serializers

from apps.intake.asset_lines import LINES, PROPERTY_KIND_WORDS, PROPERTY_KINDS, WHO
from apps.intake.serializers import AssetDetailsSerializer

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"

ENTRY = re.compile(
    r"\{ key: '(\d+)', part: (\d+), shape: '(\w+)', capacity: (\d+), "
    r"kinds: \[((?:\['\w+', \d+\](?:, )?)*)\], gate: (?:'(\d+)'|null) ?\}"
)


def _source(*path):
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    return FRONTEND.joinpath(*path).read_text()


def _flattened(text):
    """The source on one line, without the trailing commas prettier adds or its inner padding."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return re.sub(r"\[ ", "[", re.sub(r" \]", "]", text))


def _const_list(text, name):
    match = re.search(rf"export const {name} = \[(.*?)\] as const", text, re.S)
    assert match, f"{name} isn't in types/api.ts"
    return re.findall(r"'(\w+)'", match.group(1))


def test_the_wizard_asks_the_lines_the_server_knows():
    text = _source("constants", "assetLines.ts")
    block = text[text.index("export const ASSET_LINES") :]
    found = [
        (
            key,
            int(part),
            shape,
            int(capacity),
            tuple((kind, int(slots)) for kind, slots in re.findall(r"\['(\w+)', (\d+)\]", kinds)),
            gate or None,
        )
        for key, part, shape, capacity, kinds, gate in ENTRY.findall(_flattened(block))
    ]
    assert found == [
        (line.key, line.part, line.shape, line.capacity, line.kinds, line.gate) for line in LINES
    ]


def test_the_wizard_sends_only_detail_keys_the_server_keeps():
    text = _source("types", "api.ts")
    fields = AssetDetailsSerializer().fields
    text_keys = _const_list(text, "ASSET_TEXT_DETAILS")
    flag_keys = _const_list(text, "ASSET_FLAG_DETAILS")

    assert all(isinstance(fields[key], serializers.CharField) for key in text_keys)
    assert all(isinstance(fields[key], serializers.BooleanField) for key in flag_keys)
    # The three that are neither have their own lines in the AssetDetails type
    for key in ("who", "property_kinds", "percent"):
        assert re.search(rf"^  {key}\?:", text, re.M), f"AssetDetails has no {key}"
    assert {*text_keys, *flag_keys, "who", "property_kinds", "percent"} == set(fields)


def test_the_wizard_offers_the_choices_the_server_takes():
    text = _source("types", "api.ts")
    assert _const_list(text, "PROPERTY_KINDS") == list(PROPERTY_KINDS)
    assert re.findall(r"'(\w+)'", re.search(r"type AssetWho = (.*);", text).group(1)) == list(WHO)


def test_the_wizard_shows_the_property_kind_words_a_sheet_prints():
    text = _source("constants", "formText.ts")
    block = text[text.index("export const AB_PROPERTY_KIND_WORDS") :]
    block = block[: block.index("};")]
    assert re.findall(r"^  (\w+): '([^']+)',$", block, re.M) == list(PROPERTY_KIND_WORDS.items())


def test_the_wizard_names_every_kind_of_every_line_in_the_form_words():
    text = _source("constants", "formText.ts")
    block = _flattened(text[text.index("export const AB_KIND_WORDS") :])
    for line in LINES:
        if not line.kinds:
            continue
        entry = re.search(rf"'{line.key}': \{{(.*?)\}}", block)
        assert entry, f"line {line.key} has no words for its kinds"
        names = re.findall(r"'?(\w+)'?: '", entry.group(1))
        assert names == [kind for kind, _ in line.kinds]
