"""
A part can name the step that fixes each of its boxes (3c6 R8).

Business intent: a refusal sends the filer to the step of the row the box prints, not to the one
step its binding names for every row (an entry on the List of Creditors may come from Amounts
Owed, Contracts or Codebtors). A part that names none keeps today's refusals.
"""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.forms.registry import PreconditionMissing, build_parts, get_all_form_types, packet
from apps.forms.schema import load_schema
from apps.forms.services import fill_resolver
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.intake.management.commands.seed_demo_data import PERSONAS
from apps.intake.models import IntakeSession
from apps.intake.tests.builders import complete_contract

G_NUMBER_BOXES = sorted(load_schema("schedule_g").groups["g"].number_boxes.values())
BOX = "Company Name 2.6"  # row 6, page 2


def _form(values, fixes=None):
    part = {"kind": "form", "values": values, "number_boxes": G_NUMBER_BOXES}
    return part | ({"fixes": fixes} if fixes is not None else {})


def _copy(values, fixes=None):
    part = {"kind": "copy", "page": 2, "number": 1, "values": values}
    return part | ({"fixes": fixes} if fixes is not None else {})


def _too_long(*parts):
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("schedule_g", {"version": 2, "parts": list(parts)})
    return refused.value


def test_a_box_named_in_its_parts_fixes_refuses_with_that_step():
    refused = _too_long(_form({BOX: "W" * 200}, {BOX: {"step": "codebtors"}}))

    assert refused.step == "codebtors"


def test_a_part_without_fixes_refuses_with_the_bindings_step():
    refused = _too_long(_form({BOX: "W" * 200}))

    assert refused.step == "contracts"


def test_a_copy_refuses_with_its_own_fixes_not_the_form_parts():
    refused = _too_long(
        _form({BOX: "Short"}, {BOX: {"step": "debts"}}),
        _copy({BOX: "W" * 200}, {BOX: {"step": "codebtors"}}),
    )

    assert refused.step == "codebtors"


@pytest.mark.django_db
def test_only_the_list_of_creditors_stores_fixes():
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", stdout=StringIO())
    covered = set()
    for persona in PERSONAS:
        session = IntakeSession.objects.get(user__username=f"demo_{persona}")
        # A form outside the packet (122A-1Supp, until step 4) is built directly: it is no
        # persona's packet, but it must not store "fixes" either.
        for form_type in {*packet(session), *get_all_form_types()} - {"list_of_creditors"}:
            try:
                parts = build_parts(form_type, session)["parts"]
            except PreconditionMissing:
                continue  # such as 103B for a persona who pays the fee
            covered.add(form_type)
            for part in parts:
                assert "fixes" not in part, (persona, form_type)

    assert covered >= set(get_all_form_types()) - {"list_of_creditors"}


@pytest.mark.django_db
def test_a_copy_takes_the_fix_of_the_entry_it_prints_not_its_slot_row(
    generated_form_factory, monkeypatch
):
    session = generated_form_factory().session
    for n in range(1, 15):
        complete_contract(session, counterparty_name=f"Demo Lessor {n:02d}")
    steps = ["debts"] * 13 + ["codebtors"]

    def fixes(binding, _session):
        return [{"step": step} for step in steps] if binding == "claims.contracts[].name" else None

    monkeypatch.setattr(fill_resolver, "row_fixes", fixes)

    form, copy = build_parts("schedule_g", session)["parts"]

    assert form["fixes"] == {f"Company Name 2.{row}": {"step": "debts"} for row in range(1, 14)}
    # Entry 14 sits in page 2's first slot (row 6); the slot's own row would give "debts".
    assert copy["fixes"] == {BOX: {"step": "codebtors"}}
