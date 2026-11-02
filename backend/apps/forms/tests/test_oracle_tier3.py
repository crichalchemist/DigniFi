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
        "Debtor1.County": "Cook",
        "Check Box1": "/Chapter 7",
    }


def _spouse_column_2(wages, payroll_tax):
    """Schedule I column 2 for a spouse at home whose one income is wages and one deduction is
    payroll tax, every other asked line left blank and so printed 0.00."""
    wage_boxes = ("Amount 2 Debtor 2", "Amount 4 Debtor 2", "Amount 4 Debtor 2a")
    take_home = f"{float(wages) - float(payroll_tax):.2f}"
    zero_boxes = (
        *(
            f"Amount {n} Debtor 2"
            for n in ("3", "8a", "8b", "8c", "8d", "8e", "8f", "8g", "8h", "9")
        ),
        *(f"Amount 5{x} Debtor 2" for x in "bcdefgh"),
    )
    return {
        **dict.fromkeys(wage_boxes, wages),
        **dict.fromkeys(zero_boxes, "0.00"),
        "Amount 5a Debtor 2": payroll_tax,
        "Amount 6 Debtor 2": payroll_tax,
        "Amount 7 Debtor 2": take_home,
        "Amount 10 Debtor 2": take_home,
    }


def _deductions(**amounts):
    """Schedule I 5a-5h (`a`..`h`), 6 and 7 for Debtor 1; a letter not named prints 0.00."""
    boxes = {f"Amount 5{x} Debtor 1": amounts.pop(x, "0.00") for x in "abcdefgh"}
    return {
        **boxes,
        "Amount 6 Debtor 1": amounts.pop("total"),
        "Amount 7 Debtor 1": amounts.pop("pay"),
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
            "4": "3150.00",
            "5": "2560.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "3200.00",
            "CheckBox3": "/Not married",
            "CheckBox3A": "",
            "Quest11": "3200.00",
            "12B": "38400.00",
            "13B": "3",
            "13C": "113625.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            **_deductions(a="400.00", total="400.00", pay="2800.00"),
            "Amount 8b Debtor 1": "0.00",
            "Amount 8e Debtor 1": "0.00",
            "Amount 8f Debtor 1": "350.00",
            "Amount 10 Debtor 1": "3150.00",
            "Amount 10": "3150.00",
            "Amount 12": "3150.00",
        },
        "schedule_j": {
            "check2": "/yes",
            "Dependant Relation 2a": "Son",
            "Dependant age 2a": "8",
            "check2a": "/yes",
            "Dependant Relation 2b": "Daughter",
            "Dependant age 2b": "5",
            "check2b": "/yes",
            "Dependant Relation 2c": "",
            "18": "",
            "22a": "2560.00",
            "22c": "2560.00",
            "23a": "3150.00",
            "23b": "2560.00",
            "23c": "590.00",
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
            "4": "4500.00",
            "5": "3110.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "5833.00",
            "CheckBox3": "/Not married",
            "CheckBox3A": "",
            "Quest11": "5833.00",
            "12B": "69996.00",
            "13B": "1",
            "13C": "73180.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            **_deductions(a="1288.00", g="45.00", total="1333.00", pay="4500.00"),
            "Amount 8b Debtor 1": "0.00",
            "Amount 8e Debtor 1": "0.00",
            "Amount 8f Debtor 1": "0.00",
            "Amount 10 Debtor 1": "4500.00",
            "Amount 10": "4500.00",
            "Amount 12": "4500.00",
        },
        "schedule_j": {
            "check2": "/no",
            "18": "",
            "22a": "3110.00",
            "22c": "3110.00",
            "23a": "4500.00",
            "23b": "3110.00",
            "23c": "1390.00",
        },
    },
    "priya": {
        "form_101": _common("Priya", "Sharma", "456 W Fullerton Pkwy", "60614"),
        "form_106sum": {
            "1b": "8500.00",
            "1c": "8500.00",
            "3b": "57000.00",
            "3c": "57000.00",
            "4": "9880.00",
            "5": "6640.00",
            "8": "13800.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "12000.00",
            "Debto2.Quest2.0": "1800.00",
            "Debto2.Quest11": "1800.00",
            "CheckBox3": "/Married but not filing",
            "CheckBox3A": "/together",
            "Quest11": "13800.00",
            "12B": "165600.00",
            "13B": "4",
            "13C": "137902.00",
            "14a": ABOVE_MEDIAN,
        },
        "form_122a2": {"Quest1": "13800.00"},
        "schedule_i": {
            **_deductions(a="2450.00", c="600.00", e="620.00", total="3670.00", pay="8330.00"),
            "Amount 8b Debtor 1": "0.00",
            "Amount 8e Debtor 1": "0.00",
            "Amount 8f Debtor 1": "0.00",
            "Amount 10 Debtor 1": "8330.00",
            "Amount 10": "9880.00",
            "Amount 12": "9880.00",
            **_spouse_column_2("1800.00", "250.00"),
        },
        "schedule_j": {
            "check2": "/yes",
            "Dependant Relation 2a": "Daughter",
            "Dependant age 2a": "10",
            "check2a": "/yes",
            "Dependant Relation 2b": "Son",
            "Dependant age 2b": "7",
            "check2b": "/yes",
            "18": "",
            "22a": "6640.00",
            "22c": "6640.00",
            "23a": "9880.00",
            "23b": "6640.00",
            "23c": "3240.00",
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
            "4": "3935.00",
            "5": "2295.00",
            "8": "4500.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "3500.00",
            "Debto2.Quest2.0": "1000.00",
            "Debto2.Quest11": "1000.00",
            "CheckBox3": "/Married but not filing",
            "CheckBox3A": "/together",
            "Quest11": "4500.00",
            "12B": "54000.00",
            "13B": "2",
            "13C": "93934.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            **_deductions(a="450.00", total="450.00", pay="3050.00"),
            "Amount 8b Debtor 1": "0.00",
            "Amount 8e Debtor 1": "0.00",
            "Amount 8f Debtor 1": "0.00",
            "Amount 10 Debtor 1": "3050.00",
            "Amount 10": "3935.00",
            "Amount 12": "3935.00",
            **_spouse_column_2("1000.00", "115.00"),
        },
        "schedule_j": {
            "check2": "/no",
            "18": "",
            "22a": "2295.00",
            "22c": "2295.00",
            "23a": "3935.00",
            "23b": "2295.00",
            "23c": "1640.00",
        },
    },
    "sarah": {
        "form_101": _common("Sarah", "Chen", "1520 N Damen Ave Apt 2F", "60622"),
        "form_106sum": {
            "3b": "31400.00",
            "3c": "31400.00",
            "4": "1750.00",
            "5": "1280.00",
        },
        "form_122a1": {
            "Debto1.Quest7": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "2000.00",
            "CheckBox3": "/Not married",
            "CheckBox3A": "",
            "Quest11": "2000.00",
            "12B": "24000.00",
            "13B": "2",
            "13C": "93934.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            **_deductions(a="250.00", total="250.00", pay="1750.00"),
            "Amount 8b Debtor 1": "0.00",
            "Amount 8e Debtor 1": "0.00",
            "Amount 8f Debtor 1": "0.00",
            "Amount 10 Debtor 1": "1750.00",
            "Amount 10": "1750.00",
            "Amount 12": "1750.00",
        },
        "schedule_j": {
            "check2": "/no",
            "18": "",
            "22a": "1280.00",
            "22c": "1280.00",
            "23a": "1750.00",
            "23b": "1280.00",
            "23c": "470.00",
        },
    },
    # His net driving income is other income until step 3e2 (3a1 spec §2, 3a1.Q1).
    "andres": {
        "form_101": {"Debtor1.County": "Kane"},
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
            "CheckBox3": "/Not married",
            "CheckBox3A": "",
            "Quest11": "3370.00",
            "12B": "40440.00",
            "13A": "IL",
            "13B": "2",
            "13C": "93934.00",
            "14a": BELOW_MEDIAN,
        },
        "schedule_i": {
            **_deductions(total="0.00", pay="0.00"),
            "Amount 8b Debtor 1": "0.00",
            "Amount 8f Debtor 1": "0.00",
            "Other income 8h": "Other income",
            "Amount 8h Debtor 1": "3370.00",
            "Amount 10 Debtor 1": "3370.00",
            "Amount 10": "3370.00",
            "Amount 12": "3370.00",
        },
        "schedule_j": {
            "check2": "/yes",
            "Dependant Relation 2a": "Daughter",
            "Dependant age 2a": "9",
            "check2a": "/yes",
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
