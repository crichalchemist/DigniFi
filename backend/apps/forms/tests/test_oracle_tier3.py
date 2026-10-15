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
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.oracle import case_param
from apps.forms.tests.pdf_readback import read_widgets
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
            "13C": "110712.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "3200.00"},
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
            "13C": "71304.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "5833.00"},
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
            "13C": "134366.00",
            "14a": ABOVE_MEDIAN,
        },
        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "12000.00"},
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
            "13C": "91526.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "3500.00"},
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
            "13C": "71304.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "2000.00"},
        "schedule_j": {
            "18": "",
            "22a": "1280.00",
            "22c": "1280.00",
            "23a": "2000.00",
            "23b": "1280.00",
            "23c": "720.00",
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
    (form_type, full name) → what the persona's filled forms show there.

    A box shows its tick, the /AS of each widget that isn't /Off, and never its /V
    (spec §6). A text box has no /AS, and shows its /V unless that is empty. Every
    box in the filled forms has an entry, so an expected blank can't pass on a
    name that is no box.
    """
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", "--reset", persona=persona, verbosity=0)
    session = IntakeSession.objects.filter(user__username=f"demo_{persona}").latest("id")
    printed = {}
    for form_type in EXPECTED[persona]:
        values = build_field_values(form_type, session)
        for w in read_widgets(PDFFormFiller().fill(form_type, values)):
            shows = printed.setdefault((form_type, w.full_name), set())
            if w.state is None:
                shown = w.value
            elif w.state != "/Off":
                shown = w.state
            else:
                continue
            if shown:
                shows.add(shown)
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
    if expected == "":  # the box shows nothing
        assert (form_type, pdf_field) in printed, f"no box named {pdf_field!r} on {form_type}"
        assert shown == set(), f"wrong_value: prints {sorted(shown)}, expected blank"
    elif expected.startswith("/"):  # a box: this tick and no other
        assert shown == {expected}, f"wrong_value: ticks {sorted(shown)}, expected {expected}"
    elif _amount(expected) is not None:
        assert {_amount(s) for s in shown} == {
            _amount(expected)
        }, f"wrong_value: prints {sorted(shown)}, expected {expected}"
    else:
        assert expected in shown, f"wrong_value: prints {sorted(shown)}, expected {expected}"
