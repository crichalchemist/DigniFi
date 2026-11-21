"""
Signature lines and signing dates print blank (step 2 spec §3 Q6, §6.3; DIG-73).

Business intent: the filer signs each form in ink and dates it on the day they sign.
A typed name on a signature line is not their signature, and a date printed when the
packet was built is not the day they swore to it under penalty of perjury. So both stay
blank.

Form 101 (11/26) holds its signature lines as `/Sig` fields, which no binding can fill
(`schema.py` has no `Signature` binding type), so they stay blank by construction; its
dated lines are the plain boxes below.
"""

from functools import cache

import pytest
from django.core.management import call_command

from apps.forms.registry import build_field_values
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.services.widgets import template_widgets
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import IntakeSession

# Each form's Debtor 1 signature line and signing date, left blank for wet ink. Form 101's
# six are its 11/26 Part 7 date and its notice page's signature line and date.
# Priya's packet holds all five forms, 122A-2 included.
SIGNING_LINES = {
    "form_101": ["MM", "DD", " YYYY", "MM  DD_2", " YYYY_4", "undefined_23"],
    "form_106dec": ["Debtor1.signature", "Executed on"],
    "form_121": ["Debtor1.signature", "Executed on"],
    "form_122a1": ["Debtor1.sig", "Debtor1.Date signed"],
    "form_122a2": ["Debtor1.sig", "Debtor1.Date signed"],
}

# Boxes on the same form that must still print, so a blank signing line can't come from
# a form that printed nothing.
STILL_PRINTS = {
    "form_101": {"First name": "Priya", "Contact phone_2": "312-555-0303"},
    "form_106dec": {"Debtor 1": "Priya Sharma"},
    "form_121": {"Debtor1.First name": "Priya"},
    "form_122a1": {"Debtor1.Name": "Priya Sharma"},
    "form_122a2": {"Debtor1.Name": "Priya Sharma"},
}


@cache
def _printed():
    """
    (form_type, full name) → the texts Priya's drawn forms print in each drawn widget of
    that name; "" for a widget that prints nothing, so a name that prints on only some of
    its widgets shows it. Every
    box of the template has an entry, so a box name that is no box can't pass as blank.
    """
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona="priya", verbosity=0)
    session = IntakeSession.objects.get(user__username="demo_priya")
    printed = {}
    for form_type in SIGNING_LINES:
        values = build_field_values(form_type, session)
        template = load_schema(form_type).template_filename
        drawn = {(w.page, w.tag) for w in template_widgets(template) if w.drawn}
        for widget in read_drawn(form_type, PDFFormFiller().fill(form_type, values)):
            if (widget.page, widget.tag) in drawn:
                printed.setdefault((form_type, widget.full_name), set()).add(widget.value)
    return printed


@pytest.mark.slow
@pytest.mark.django_db
@pytest.mark.parametrize(
    "form_type,box",
    [(form_type, box) for form_type, boxes in SIGNING_LINES.items() for box in boxes],
)
def test_signature_lines_and_signing_dates_stay_blank_for_wet_ink(form_type, box):
    printed = _printed()
    assert (form_type, box) in printed, f"no box named {box!r} on {form_type}"
    assert printed[(form_type, box)] == {""}
    # Every widget of each neighbour prints it: a page header blank on one page fails.
    for neighbour, value in STILL_PRINTS[form_type].items():
        assert printed[(form_type, neighbour)] == {value}
