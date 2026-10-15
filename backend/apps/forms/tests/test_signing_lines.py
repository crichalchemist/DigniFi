"""
Signature lines and signing dates print blank (step 2 spec §3 Q6, §6.3; DIG-73).

Business intent: the filer signs each form in ink and dates it on the day they sign.
A typed name on a signature line is not their signature, and a date printed when the
packet was built is not the day they swore to it under penalty of perjury. So both stay
blank, even for a filer who gave a signing date or named an attorney.
"""

from functools import cache

import pytest
from django.core.management import call_command

from apps.forms.registry import build_field_values
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import FormAnswer, IntakeSession

# Each form's Debtor 1 signature line and signing date that held a binding before Q6.
# Priya's packet holds all five forms, 122A-2 included.
SIGNING_LINES = {
    "form_101": ["Executed on", "Attorney.Date signed"],
    "form_106dec": ["Debtor1.signature", "Executed on"],
    "form_121": ["Debtor1.signature", "Executed on"],
    "form_122a1": ["Debtor1.sig", "Debtor1.Date signed"],
    "form_122a2": ["Debtor1.sig", "Debtor1.Date signed"],
}

# Boxes on the same form that must still print, so a blank signing line can't come from
# a form that printed nothing, or from an attorney block that was never switched on.
STILL_PRINTS = {
    "form_101": {"Debtor1.First name": "Priya", "Attorney.Printed name": "Ann Lee"},
    "form_106dec": {"Debtor 1": "Priya Sharma"},
    "form_121": {"Debtor1.First name": "Priya"},
    "form_122a1": {"Debtor1.Name": "Priya Sharma"},
    "form_122a2": {"Debtor1.Name": "Priya Sharma"},
}


@cache
def _printed():
    """
    (form_type, full name) → the text Priya's filled forms show there, once she has given
    a signing date and named an attorney. Every box in the filled forms has an entry, so a
    box name that is no box can't pass as blank.
    """
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona="priya", verbosity=0)
    session = IntakeSession.objects.get(user__username="demo_priya")
    for form_type, key, value in [
        ("form_107", "attorney_gate", "yes"),
        ("form_101", "attorney_printed_name", "Ann Lee"),
        ("form_101", "executed_on", "10/14/2026"),
        ("form_101", "attorney_date_signed", "10/14/2026"),
    ]:
        FormAnswer.objects.create(session=session, form_type=form_type, field_key=key, value=value)
    printed = {}
    for form_type in SIGNING_LINES:
        values = build_field_values(form_type, session)
        for widget in read_widgets(PDFFormFiller().fill(form_type, values)):
            shows = printed.setdefault((form_type, widget.full_name), set())
            if widget.value:
                shows.add(widget.value)
    return printed


@pytest.mark.django_db
@pytest.mark.parametrize(
    "form_type,box",
    [(form_type, box) for form_type, boxes in SIGNING_LINES.items() for box in boxes],
)
def test_signature_lines_and_signing_dates_stay_blank_for_wet_ink(form_type, box):
    printed = _printed()
    assert (form_type, box) in printed, f"no box named {box!r} on {form_type}"
    assert printed[(form_type, box)] == set()
    for neighbour, value in STILL_PRINTS[form_type].items():
        assert printed[(form_type, neighbour)] == {value}
