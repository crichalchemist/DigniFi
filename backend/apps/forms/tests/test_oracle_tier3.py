"""
Oracle tier 3: each seeded persona's packet prints the figures a correct filing must (spec §6).

Expected values are worked out by hand from each persona's data (the seed, which
matches docs/testing/persona-briefs/ except Priya's stale income line), never
from the app's derivations. Boxes are named from the verified field index, not
from the schema, so a value bound to the wrong line fails here. Money compares
as a number, so "3,200.00" equals "3200.00". An expected "" means the box shows
nothing (step 2 spec §7.5): a line DigniFi never asks prints blank, and so does
an expense at $0, but an income source typed as $0 prints 0.00.
"""

from decimal import Decimal, InvalidOperation
from functools import cache

import pytest
from django.core.management import call_command

from apps.districts.models import District
from apps.forms.registry import build_field_values
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.services.widgets import template_widgets
from apps.forms.tests.oracle import case_param
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import IntakeSession

TIER = "3"
BELOW_MEDIAN = "/12b less or equal to 13"
ABOVE_MEDIAN = "/12b more than 13"


def _common(first, last, street, zip_code):
    return {
        "Debtor1.First name": first,
        "Debtor1.Last name": last,
        "Debtor1.Street": street,
        "Debtor1.City": "Chicago",
        "Debtor1.State": "IL",
        "Debtor1.ZIP Code": zip_code,
        "Check Box1": "/Chapter 7",
    }


# persona → form_type → full name → printed value
EXPECTED = {
    "maria": {
        "form_101": _common("Maria", "Torres", "2145 W Division St Apt 3", "60622"),
        "form_106sum": {
            "1b": "6840.00",
            "1c": "6840.00",
            "3b": "20500.00",
            "3c": "20500.00",
            "4": "3200.00",
            "5": "2560.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "3200.00",
            "Quest11": "3200.00",
            "12B": "38400.00",
            "13B": "3",
            "13C": "113625.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            "Amount 8b Debtor 1": "",
            "Amount 8e Debtor 1": "0.00",
            "Amount 12": "3200.00",
        },
        "schedule_j": {
            "18": "",
            "22a": "2560.00",
            "22c": "2560.00",
            "23a": "3200.00",
            "23b": "2560.00",
            "23c": "640.00",
        },
    },
    "james": {
        "form_101": _common("James", "Washington", "850 N State St Apt 1204", "60610"),
        "form_106sum": {
            "1b": "15200.00",
            "1c": "15200.00",
            "2": "8500.00",
            "3b": "9800.00",
            "3c": "18300.00",
            "4": "5833.00",
            "5": "3110.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "5833.00",
            "Quest11": "5833.00",
            "12B": "69996.00",
            "13B": "1",
            "13C": "73180.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            "Amount 8b Debtor 1": "",
            "Amount 8e Debtor 1": "0.00",
            "Amount 12": "5833.00",
        },
        "schedule_j": {
            "18": "",
            "22a": "3110.00",
            "22c": "3110.00",
            "23a": "5833.00",
            "23b": "3110.00",
            "23c": "2723.00",
        },
    },
    "priya": {
        "form_101": _common("Priya", "Sharma", "456 W Fullerton Pkwy", "60614"),
        "form_106sum": {
            "1b": "8500.00",
            "1c": "8500.00",
            "3b": "57000.00",
            "3c": "57000.00",
            "4": "12000.00",
            "5": "6640.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Quest11": "12000.00",
            "12B": "144000.00",
            "13B": "4",
            "13C": "137902.00",
            "14a": ABOVE_MEDIAN,
        },
        "schedule_i": {
            "Amount 8b Debtor 1": "",
            "Amount 8e Debtor 1": "0.00",
            "Amount 12": "12000.00",
        },
        "schedule_j": {
            "18": "",
            "22a": "6640.00",
            "22c": "6640.00",
            "23a": "12000.00",
            "23b": "6640.00",
            "23c": "5360.00",
        },
    },
    "deshawn": {
        "form_101": _common("DeShawn", "Mitchell", "7823 S Sangamon St", "60620"),
        "form_106sum": {
            "1a": "180000.00",
            "1b": "20000.00",
            "1c": "200000.00",
            "2": "160000.00",
            "3b": "11700.00",
            "3c": "171700.00",
            "4": "3500.00",
            "5": "2295.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Quest11": "3500.00",
            "12B": "42000.00",
            "13B": "2",
            "13C": "93934.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            "Amount 8b Debtor 1": "",
            "Amount 8e Debtor 1": "0.00",
            "Amount 12": "3500.00",
        },
        "schedule_j": {
            "18": "",
            "22a": "2295.00",
            "22c": "2295.00",
            "23a": "3500.00",
            "23b": "2295.00",
            "23c": "1205.00",
        },
    },
    "sarah": {
        "form_101": _common("Sarah", "Chen", "1520 N Damen Ave Apt 2F", "60622"),
        "form_106sum": {
            "3b": "31400.00",
            "3c": "31400.00",
            "4": "2000.00",
            "5": "1280.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "2000.00",
            "Quest11": "2000.00",
            "12B": "24000.00",
            "13B": "1",
            "13C": "73180.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            "Amount 8b Debtor 1": "",
            "Amount 8e Debtor 1": "0.00",
            "Amount 12": "2000.00",
        },
        "schedule_j": {
            "18": "",
            "22a": "1280.00",
            "22c": "1280.00",
            "23a": "2000.00",
            "23b": "1280.00",
            "23c": "720.00",
        },
    },
    # His net driving income is other income until step 3e2 (3a1 spec §2, 3a1.Q1).
    "andres": {
        "form_106sum": {
            "1a": "0.00",
            "1b": "6697.00",
            "1c": "6697.00",
            "2": "7800.00",
            "3a": "",
            "3b": "23160.00",
            "3c": "30960.00",
            "4": "3370.00",
            "5": "2779.00",
        },
        "form_122a1": {
            "CheckBox1": "/No Abuse",
            "terrorism If necessary list other sources on a separate page and put the total below 1": "Other income",
            "Debto1.Quest10A": "3370.00",
            "Debto1.Quest11": "3370.00",
            "Quest11": "3370.00",
            "12B": "40440.00",
            "13A": "IL",
            "13B": "2",
            "13C": "93934.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            "Other income 8h": "Other income",
            "Amount 8h Debtor 1": "3370.00",
            "Amount 10 Debtor 1": "3370.00",
            "Amount 10": "3370.00",
            "Amount 12": "3370.00",
        },
        "schedule_j": {
            "17a": "389.00",
            "22a": "2779.00",
            "22c": "2779.00",
            "23a": "3370.00",
            "23b": "2779.00",
            "23c": "591.00",
        },
    },
}


def _cases():
    for persona, forms in EXPECTED.items():
        for form_type, boxes in forms.items():
            for full_name, expected in boxes.items():
                yield case_param(form_type, full_name, TIER, persona, expected)


CASES = list(_cases())


@cache
def _printed(persona):
    """
    (form_type, full name) → what the persona's drawn forms print there.

    A box shows its tick: the state of each of its widgets with the check mark printed
    inside (spec §6, 3a2 spec §8). A text box shows the text printed in each of its
    drawn widgets, "" for one that prints nothing, so every widget of the name must
    print the expected text. Every box of the template has an entry, so an expected
    blank can't pass on a name that is no box.
    """
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", "--reset", persona=persona, verbosity=0)
    session = IntakeSession.objects.filter(user__username=f"demo_{persona}").latest("id")
    printed = {}
    for form_type in EXPECTED[persona]:
        values = build_field_values(form_type, session)
        template = load_schema(form_type).template_filename
        drawn = {(w.page, w.tag) for w in template_widgets(template) if w.drawn}
        for w in read_drawn(form_type, PDFFormFiller().fill(form_type, values)):
            if (w.page, w.tag) not in drawn:
                continue
            shows = printed.setdefault((form_type, w.full_name), set())
            if not w.state:
                shows.add(w.value)
            elif w.state != "/Off":
                shows.add(w.state)
    return printed


def _amount(text):
    try:
        return Decimal(text.replace("$", "").replace(",", "").strip())
    except InvalidOperation:
        return None


@pytest.mark.django_db
@pytest.mark.parametrize("form_type,pdf_field,case,expected", CASES)
def test_persona_packet_prints_the_right_figure(form_type, pdf_field, case, expected):
    printed = _printed(case)
    shown = printed.get((form_type, pdf_field), set())
    if expected == "":  # the box shows nothing, in any of its widgets
        assert (form_type, pdf_field) in printed, f"no box named {pdf_field!r} on {form_type}"
        assert shown <= {""}, f"wrong_value: prints {sorted(shown - {''})}, expected blank"
    elif expected.startswith("/"):  # a box: this tick and no other
        assert shown == {expected}, f"wrong_value: ticks {sorted(shown)}, expected {expected}"
    elif _amount(expected) is not None:  # every widget prints it; a blank one is no amount
        assert {_amount(s) for s in shown} == {
            _amount(expected)
        }, f"wrong_value: prints {sorted(shown)}, expected {expected}"
    else:  # every widget prints it
        assert shown == {expected}, f"wrong_value: prints {sorted(shown)}, expected {expected}"
