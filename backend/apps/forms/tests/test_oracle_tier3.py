"""
Oracle tier 3: each seeded persona's packet prints the figures a correct filing must (spec §6).

Expected values are worked out by hand from each persona's data (the seed, which
matches docs/testing/persona-briefs/ except Priya's stale income line), never
from the app's derivations. Boxes are named from the verified field index, not
from the schema, so a value bound to the wrong line fails here. Money (an expected
value with two decimals) compares as a number, so "3,200.00" equals "3200.00";
anything else compares as written, so a cited line "4.2" never passes for "4.20".
An expected "" means the box shows
nothing (step 2 spec §7.5): a line DigniFi never asks prints blank, and so does
an expense at $0, but an income source typed as $0 prints 0.00.
"""

import re
from decimal import Decimal, InvalidOperation
from functools import cache

import pytest
from django.core.management import call_command

from apps.districts.models import District
from apps.forms.registry import build_field_values, build_parts
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.services.sheets import sheet_spec
from apps.forms.services.widgets import template_widgets
from apps.forms.tests.oracle import case_param
from apps.forms.tests.pdf_readback import read_drawn, read_sheets
from apps.forms.tests.test_form_122a1_schema import LINE_10_SOURCE
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


# Column B lines 3-10 print 0.00 for a spouse at home with those sources typed $0 (§11)
COLUMN_B_ZEROS = [
    "Debto2.Quest3",
    "Debto2.Quest2.2",
    "Debto2.Quest5A",
    "Debto2.Quest5B",
    "Debto2.Quest5C",
    "Debto2.Quest6A",
    "Debto2.Quest6B",
    "Debto2.Quest6C",
    "Debto2.Quest7",
    "Debto2.Quest8.0",
    "Debto2.Quest9",
    "Debto2.Quest10A",
]

LINE_4_QUESTION = (
    "Examples Boats trailers motors personal watercraft fishing vessels snowmobiles "
    "motorcycle accessories"
)


def _no_lines(*boxes):
    """Schedule A/B lines the persona answered No: every one of these boxes' No exports /no."""
    return dict.fromkeys(boxes, "/no")


def _own_car(make, model, year, miles, value):
    """Schedule A/B 3.1 for a car owned outright and alone: the same figure in both value boxes."""
    return {
        "Check 3": "/yes",
        "3 1": make,
        "3 2": model,
        "3 3": year,
        "3 4": miles,
        "Who has interest in property 4": "/Debtor 1",
        "undefined_14": value,
        "undefined_15": value,
    }


# persona → form_type → full name → printed value
EXPECTED = {
    "maria": {
        "form_101": {
            **_common("Maria", "Torres", "2145 W Division St Apt 3", "60622"),
            "Check Box7": "/Request fees waived",
        },
        "form_103b": {
            "You": "/On",
            "Your spouse": "",
            "Your dependents": "/On",
            "How many dependents": "2",
            "Total number of people": "3",
            "undefined_2": "3150.00",
            "undefined_3": "",
            "undefined_4": "3150.00",
            "undefined_5": "350.00",
            "undefined_6": "2800.00",
            "check 3": "/yes",
            "3 type": "SNAP (food stamps)",
        },
        # Schedule A/B totals, hand-worked: 5 = 6,500 (Civic); 15 = 600+200+250; 36 = 40 cash + 340 checking + 0 insurance; 62 = 63 = 6,500+1,050+380
        "schedule_a_b": {
            "undefined_26": "6500.00",
            "15 amount": "1050.00",
            "undefined_124": "380.00",
            "undefined_159": "0.00",
            "undefined_166": "7930.00",
            "undefined_167": "7930.00",
            # Her lines, PS:154-171. Line 31 is a typed $0: it prints, and the box is the company's.
            **_own_car("Honda", "Civic", "2015", "120000", "6500.00"),
            "Check 2": "/On",
            LINE_4_QUESTION: "/No_2",
            "6 check": "/yes",
            "6 description": "Beds, sofa, kitchen table, dishes",
            "6 description amount": "600.00",
            "7 description": "Old laptop, cell phone, 32-inch TV",
            "7 description amount": "200.00",
            "11 description": "Everyday clothes and shoes",
            "11 description amount": "250.00",
            "Check 16": "/yes",
            "16 Cash amount": "40.00",
            "Check 17": "/yes",
            "17.1 Checking account": "JPMorgan Chase",
            "17.1 Checking amount": "340.00",
            "17.2 Checking account": "",
            "check 31": "/yes",
            "Company name 1": "Millbrook Mutual Life",
            "Beneficiary 1": "",
            "undefined_109": "0.00",
            "undefined_110": "",
            **_no_lines("check 21", "check 22", "check 28", "check 29", "check 37", "check 46"),
            **_no_lines("check 53"),
        },
        "form_106sum": {
            "1b": "7930.00",
            "1c": "7930.00",
            "2": "0.00",
            "3b": "20500.00",
            "3c": "20500.00",
            "4": "3150.00",
            "5": "2600.00",
        },
        "form_122a1": {
            **dict.fromkeys(
                ["Debto1.Quest5A", "Debto1.Quest5B", "Debto1.Quest5C"]
                + ["Debto1.Quest6A", "Debto1.Quest6B", "Debto1.Quest6C", "Debto1.Quest7"],
                "0.00",
            ),
            "Debto1.Quest8A": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "3200.00",
            "Debto2.Quest5C": "",
            "Debto2.Quest7": "",
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
            "check3": "/no",
            "4b": "",
            "10": "40.00",
            "13": "",
            "14": "",
            "16": "",
            "Other 16": "",
            "Other 21": "School supplies and fees",
            "4": "1100.00",
            "22a": "2600.00",
            "22c": "2600.00",
            "23a": "3150.00",
            "23b": "2600.00",
            "23c": "550.00",
        },
        # Her rows (3c5 spec §9.6). No secured debt: D's last-page total prints 0.00, as 106Sum 2.
        "schedule_d": {"undefined_24": "0.00"},
        # E/F in creditor order; her two collectors cite the card (4.1) and the hospital (4.3).
        "schedule_e_f": {
            "check1": "/no",
            "Total_6a": "0.00",
            "Total_6b": "0.00",
            "Total_6c": "0.00",
            "Total_6d": "0.00",
            "Total_6e": "0.00",
            "Creditors Name_6": "Brightwater Card Services",
            "Creditors Name_7": "Ironbridge Card Company",
            "Creditors Name_8": "Larkfield General Hospital",
            "Creditors Name_12": "Lakefront Demo Recovery LLC",
            "Referenced line 5.1": "4.1",
            "Creditors Name_13": "Prairie Demo Collections Inc.",
            "Referenced line 5.2": "4.3",
        },
        "schedule_g": {"Company Name 2.1": "Division Demo Properties LLC"},
        "schedule_h": {"check1": "/no"},
        "list_of_creditors": {
            "creditor1.0.0": "Brightwater Card Services 1 Demo Way Richmond, VA 23238",
            "creditor1.0.1": "Ironbridge Card Company 3 Demo Rd Riverwoods, IL 60015",
            "creditor1.0.2": "Larkfield General Hospital 2 Demo Plaza Chicago, IL 60611",
            "creditor1.0.3": "Lakefront Demo Recovery LLC 10 Demo Ct Chicago, IL 60604",
            "creditor1.0.4": "Prairie Demo Collections Inc. 20 Demo Ave Oak Brook, IL 60523",
            "creditor2.0.0": "Division Demo Properties LLC 30 Demo St Chicago, IL 60622",
            "creditor2.0.1": "",
        },
    },
    "james": {
        "form_101": {
            **_common("James", "Washington", "850 N State St Apt 1204", "60610"),
            "Check Box7": "/Pay entirely",
        },
        # Schedule A/B totals, hand-worked: 5 = 14,000 (Camry); 15 = 500+400+300; 36 = 40 cash + 1,200 checking; 62 = 63 = 14,000+1,200+1,240
        "schedule_a_b": {
            "undefined_26": "14000.00",
            "15 amount": "1200.00",
            "undefined_124": "1240.00",
            "undefined_159": "0.00",
            "undefined_166": "16440.00",
            "undefined_167": "16440.00",
            # His lines, PS:394-399. His "Wallet" under line 16 isn't stored: the line has no text box.
            **_own_car("Toyota", "Camry", "2019", "78000", "14000.00"),
            "6 description": "Bed, couch, table, kitchenware (secondhand)",
            "6 description amount": "500.00",
            "7 description": "TV, laptop, cell phone",
            "7 description amount": "400.00",
            "11 description": "Everyday clothes and work clothes",
            "11 description amount": "300.00",
            "Check 16": "/yes",
            "16 Cash amount": "40.00",
            "Check 17": "/yes",
            "17.1 Checking account": "Bank of America",
            "17.1 Checking amount": "1200.00",
            **_no_lines("check 21", "check 22", "check 28", "check 29", "check 31"),
            **_no_lines("check 37", "check 46", "check 53"),
        },
        "form_106sum": {
            "1b": "16440.00",
            "1c": "16440.00",
            "2": "8500.00",
            "3b": "9800.00",
            "3c": "18300.00",
            "4": "4500.00",
            "5": "3210.00",
        },
        "form_122a1": {
            **dict.fromkeys(
                ["Debto1.Quest5A", "Debto1.Quest5B", "Debto1.Quest5C"]
                + ["Debto1.Quest6A", "Debto1.Quest6B", "Debto1.Quest6C", "Debto1.Quest7"],
                "0.00",
            ),
            "Debto1.Quest8A": "",
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
            "check3": "/no",
            "4b": "15.00",
            "10": "40.00",
            "13": "45.00",
            "14": "",
            "16": "",
            "Other 16": "",
            "Other 21": "Work boots and small tools for my job",
            "4": "1650.00",
            "17a": "350.00",
            "22a": "3210.00",
            "22c": "3210.00",
            "23a": "4500.00",
            "23b": "3210.00",
            "23c": "1290.00",
        },
        # His rows (§9.6). The Camry is his alone: B = its 14,000, C = 8,500 less 14,000, floored
        # at 0.00. D's last-page total equals 106Sum 2.
        "schedule_d": {
            "Creditors Name": "Crestway Auto Credit",
            "undefined": "8500.00",
            "undefined_2": "14000.00",
            "undefined_3": "0.00",
            "undefined_24": "8500.00",
        },
        "schedule_e_f": {
            "check1": "/no",
            "Total_6a": "0.00",
            "Total_6b": "0.00",
            "Total_6c": "0.00",
            "Total_6d": "0.00",
            "Total_6e": "0.00",
            "Creditors Name_6": "Meridale National Bank",
            "Total_26": "9800.00",
            "Other unsecurecured claim 4.1": "Credit card",
        },
        "schedule_g": {
            "Company Name 2.1": "Gold Coast Example Residential LLC",
            "Street 2.1": "850 N State St, c/o Management Office",
        },
        "schedule_h": {"check1": "/no"},
        "list_of_creditors": {
            "creditor1.0.0": "Crestway Auto Credit PO Box 90122 Plano, TX 75025",
            "creditor1.0.1": "Meridale National Bank PO Box 90222 Sioux Falls, SD 57117",
            "creditor1.0.2": "Gold Coast Example Residential LLC 850 N State St c/o Management Office Chicago, IL 60610",
            "creditor1.0.3": "",
        },
    },
    "priya": {
        "form_101": {
            **_common("Priya", "Sharma", "456 W Fullerton Pkwy", "60614"),
            "Check Box7": "/Pay entirely",
        },
        # Schedule A/B totals, hand-worked: 5 = 20,500 (CR-V); 15 = 2,500+1,500+800+1,200; 36 = 1,900+8,500+31,000+0+0; 62 = 63 = 20,500+6,000+41,400
        "schedule_a_b": {
            "undefined_26": "20500.00",
            "15 amount": "6000.00",
            "undefined_124": "41400.00",
            "undefined_159": "0.00",
            "undefined_166": "67900.00",
            "undefined_167": "67900.00",
            # Her lines, PS:629-637, her savings on 17.3 because the form prints 17.2 as
            # checking (3b spec §10), and her two policies each at a typed $0.
            **_own_car("Honda", "CR-V EX", "2021", "41000", "20500.00"),
            "6 description": "Household goods and furniture",
            "6 description amount": "2500.00",
            "7 description": "Family laptop, two phones, TV",
            "7 description amount": "1500.00",
            "11 description": "Clothes",
            "11 description amount": "800.00",
            "12 description": "Wedding and engagement rings",
            "12 description amount": "1200.00",
            "Check 16": "/no",
            "Check 17": "/yes",
            "17.1 Checking account": "JPMorgan Chase",
            "17.1 Checking amount": "1900.00",
            "17.2 Checking account": "",
            "17.2 Checking amount": "",
            "17.3 Checking account": "JPMorgan Chase",
            "17.3 Checking amount": "8500.00",
            "check 21": "/yes",
            "21.1 401k or similar plan": "Vanguard",
            "21.1 401k or similar plan amount": "31000.00",
            "check 31": "/yes",
            "Company name 1": "Wrenfield Life",
            "Beneficiary 1": "Spouse",
            "undefined_109": "0.00",
            "Company name 2": "Alderbrook Assurance",
            "Beneficiary 2": "",
            "undefined_110": "0.00",
            "Company name 3": "",
            "undefined_111": "",
            **_no_lines("check 22", "check 28", "check 29", "check 37", "check 46", "check 53"),
        },
        "form_106sum": {
            "1b": "67900.00",
            "1c": "67900.00",
            "2": "14900.00",
            "3a": "3000.00",
            "3b": "57000.00",
            "3c": "74900.00",
            "4": "9880.00",
            "5": "7050.00",
            "8": "13800.00",
            "9b": "3000.00",
            "9g": "3000.00",
        },
        "form_122a1": {
            **dict.fromkeys(
                ["Debto1.Quest5A", "Debto1.Quest5B", "Debto1.Quest5C"]
                + ["Debto1.Quest6A", "Debto1.Quest6B", "Debto1.Quest6C", "Debto1.Quest7"],
                "0.00",
            ),
            "Debto1.Quest8A": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "12000.00",
            "Debto2.Quest2.0": "1800.00",
            **dict.fromkeys(COLUMN_B_ZEROS, "0.00"),
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
            "check3": "/yes",
            "4b": "20.00",
            "10": "60.00",
            "13": "80.00",
            "14": "50.00",
            "16": "200.00",
            "Other 16": "IRS installment agreement, 2025 tax",
            "Other 21": "Children's after-school activities",
            "4": "2800.00",
            "17a": "450.00",
            "22a": "7050.00",
            "22c": "7050.00",
            "23a": "9880.00",
            "23b": "7050.00",
            "23c": "2830.00",
        },
        # Her rows (§9.6). The CR-V is hers alone: B = its 20,500, C = 14,900 less 20,500,
        # floored at 0.00. Rohan co-signed Westhaven, so 4.2 owes with another and H cites it.
        "schedule_d": {
            "Creditors Name": "Kestrel Auto Finance",
            "undefined": "14900.00",
            "undefined_2": "20500.00",
            "undefined_3": "0.00",
            "undefined_24": "14900.00",
        },
        "schedule_e_f": {
            "check1": "/yes",
            "Total_6a": "0.00",
            "Total_6b": "3000.00",
            "Total_6c": "0.00",
            "Total_6d": "0.00",
            "Total_6e": "3000.00",
            "Creditors Name": "Internal Revenue Service",
            "account number": "0003",
            "Street": "Centralized Insolvency Operation",
            "1": "P.O. Box 7346",
            "2": "Philadelphia",
            "3": "PA",
            "4": "19101-7346",
            "Date debt was incurred": "tax year 2025",
            "undefined": "3000.00",
            "undefined_2": "3000.00",
            "undefined_3": "",
            "Taxes and ceratin other debts you owe the government": "/On",
            "Creditors Name_6": "Silverpine Card Services",
            "check 6": "/debtor 1",
            "Creditors Name_7": "Westhaven University Medical Center",
            "check 7": "/On",
            "Creditors Name_12": "Lakeshore Medical Recovery LLC",
            "Referenced line 5.1": "4.2",
        },
        "schedule_g": {"Company Name 2.1": "Fullerton Parkway Apartments LLC"},
        "schedule_h": {
            "Codebtor Name 3.1": "Rohan Sharma",
            "check schedule line D 3.1": "",
            "check schedule line E/F 3.1": "/yes",
            "Schedule line E/F 3.1": "4.2",
            "check schedule line G 3.1": "",
        },
        "list_of_creditors": {
            "creditor1.0.0": "Kestrel Auto Finance P.O. Box 9303 Torrance, CA 90503",
            "creditor1.0.1": "Internal Revenue Service Centralized Insolvency Operation P.O. Box 7346 Philadelphia, PA 19101-7346",
            "creditor1.0.2": "Silverpine Card Services P.O. Box 9313 El Paso, TX 79998",
            "creditor1.0.3": "Westhaven University Medical Center 1653 W Congress Pkwy Chicago, IL 60612",
            "creditor1.0.4": "Lakeshore Medical Recovery LLC P.O. Box 9333 Chicago, IL 60690",
            "creditor2.0.0": "Fullerton Parkway Apartments LLC 456 W Fullerton Pkwy Management Office Chicago, IL 60614",
            "creditor2.0.1": "Rohan Sharma 456 W Fullerton Pkwy Chicago, IL 60614",
            "creditor2.0.2": "",
        },
    },
    "deshawn": {
        "form_101": {
            **_common("DeShawn", "Mitchell", "7823 S Sangamon St", "60620"),
            "Check Box7": "/Pay in installments",
        },
        # Schedule A/B totals, hand-worked: 55 = 180,000 (home); 5 = 8,000 (F-150); 15 = 1,500+400+300+600; 36 = 60+640+12,000; 62 = 8,000+2,800+12,700; 63 = 180,000+23,500
        "schedule_a_b": {
            "undefined_26": "8000.00",
            "15 amount": "2800.00",
            "undefined_124": "12700.00",
            "undefined_159": "180000.00",
            "undefined_166": "23500.00",
            "undefined_167": "203500.00",
            # His lines: the home is the persona with Part 1.
            "Check 2": "/yes",
            "1 1": "7823 S Sangamon St",
            "City": "Chicago",
            "State": "IL",
            "ZIP Code": "60620",
            "County": "Cook",
            "Singlefamily home": "/On",
            "the entireties or a life estate if known": "Fee simple",
            "Who has interest in property": "/Debtor 1",
            "undefined_2": "180000.00",
            "undefined_3": "180000.00",
            "undefined_13": "180000.00",
            **_own_car("Ford", "F-150", "2012", "168000", "8000.00"),
            "6 description": "Furniture, appliances and beds",
            "6 description amount": "1500.00",
            "7 description": "TV, laptop and phone",
            "7 description amount": "400.00",
            "11 description": "Everyday clothes and work boots",
            "11 description amount": "300.00",
            "12 description": "Wedding band and watch",
            "12 description amount": "600.00",
            "Check 16": "/yes",
            "16 Cash amount": "60.00",
            "17.1 Checking account": "PNC Bank",
            "17.1 Checking amount": "640.00",
            "21.1 401k or similar plan": "Fidelity",
            "21.1 401k or similar plan amount": "12000.00",
            **_no_lines("check 22", "check 28", "check 29", "check 31", "check 37", "check 46"),
            **_no_lines("check 53"),
        },
        "form_106sum": {
            "1a": "180000.00",
            "1b": "23500.00",
            "1c": "203500.00",
            "2": "160000.00",
            "3b": "11700.00",
            "3c": "171700.00",
            "4": "3935.00",
            "5": "2410.00",
            "8": "4500.00",
        },
        "form_122a1": {
            **dict.fromkeys(
                ["Debto1.Quest5A", "Debto1.Quest5B", "Debto1.Quest5C"]
                + ["Debto1.Quest6A", "Debto1.Quest6B", "Debto1.Quest6C", "Debto1.Quest7"],
                "0.00",
            ),
            "Debto1.Quest8A": "",
            "Debto1.Quest9": "0.00",
            "Debto1.Quest11": "3500.00",
            "Debto2.Quest2.0": "1000.00",
            **dict.fromkeys(COLUMN_B_ZEROS, "0.00"),
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
            "check3": "/yes",
            "4b": "",
            "10": "40.00",
            "13": "25.00",
            "14": "50.00",
            "16": "",
            "Other 16": "",
            "Other 21": "Printer ink, paper and postage",
            "4": "1200.00",
            "5": "",
            "20a": "",
            "22a": "2410.00",
            "22c": "2410.00",
            "23a": "3935.00",
            "23b": "2410.00",
            "23c": "1525.00",
        },
        # His rows (§9.6). The home is his alone: B = its 180,000, C = 160,000 less 180,000,
        # floored at 0.00. His collectors cite the electric bill (4.1) and the clinic (4.2).
        "schedule_d": {
            "Creditors Name": "Harrowgate Home Loans",
            "undefined": "160000.00",
            "undefined_2": "180000.00",
            "undefined_3": "0.00",
            "undefined_24": "160000.00",
        },
        "schedule_e_f": {
            "check1": "/no",
            "Total_6a": "0.00",
            "Total_6b": "0.00",
            "Total_6c": "0.00",
            "Total_6d": "0.00",
            "Total_6e": "0.00",
            "Creditors Name_6": "Lakeline Electric",
            "Creditors Name_7": "Southmoor Health",
            "Creditors Name_8": "Tallgrass Credit Management",
            "Creditors Name_12": "Demo Recovery Services",
            "Referenced line 5.1": "4.1",
            "Creditors Name_13": "Demo Medical Collections",
            "Referenced line 5.2": "4.2",
        },
        "schedule_g": {"check1": "/no", "Company Name 2.1": ""},
        "schedule_h": {"check1": "/no", "Codebtor Name 3.1": ""},
        "list_of_creditors": {
            "creditor1.0.0": "Harrowgate Home Loans PO Box 4401 Chicago, IL 60680",
            "creditor1.0.1": "Lakeline Electric PO Box 4403 Chicago, IL 60680",
            "creditor1.0.2": "Southmoor Health PO Box 4404 Chicago, IL 60680",
            "creditor1.0.3": "Tallgrass Credit Management PO Box 4402 Chicago, IL 60680",
            "creditor1.0.4": "Demo Recovery Services PO Box 4405 Chicago, IL 60680",
            "creditor2.0.0": "Demo Medical Collections PO Box 4406 Chicago, IL 60680",
            "creditor2.0.1": "",
        },
    },
    "sarah": {
        "form_101": {
            **_common("Sarah", "Chen", "1520 N Damen Ave Apt 2F", "60622"),
            "Check Box7": "/Request fees waived",
        },
        # Guard: passes before 3f Task 2 (her typed application equals her Income step
        # figures); Maria's entry fails first.
        "form_103b": {
            "You": "/On",
            "Your spouse": "",
            "Your dependents": "",
            "How many dependents": "",
            "Total number of people": "1",
            "undefined_2": "1750.00",
            "undefined_3": "",
            "undefined_4": "1750.00",
            "undefined_5": "",
            "undefined_6": "1750.00",
            "check 3": "/no",
            "3 type": "",
        },
        # She walked every line and answered No to each: nothing owned, every total 0.00.
        "schedule_a_b": {
            "undefined_26": "0.00",
            "15 amount": "0.00",
            "undefined_124": "0.00",
            "undefined_158": "0.00",
            "undefined_159": "0.00",
            "undefined_166": "0.00",
            "undefined_167": "0.00",
            "Check 2": "/On",
            "undefined_13": "",
            LINE_4_QUESTION: "/No_2",
            **_no_lines("Check 3", "6 check", "Check 16", "Check 17", "check 21", "check 22"),
            **_no_lines("check 28", "check 29", "check 31", "check 37", "check 46", "check 53"),
            "check 38": "",  # under line 37's No
            "check 47": "",  # under line 46's No
        },
        "form_106sum": {
            "2": "0.00",
            "3b": "31400.00",
            "3c": "31400.00",
            "4": "1750.00",
            "5": "1280.00",
        },
        "form_122a1": {
            **dict.fromkeys(
                ["Debto1.Quest5A", "Debto1.Quest5B", "Debto1.Quest5C"]
                + ["Debto1.Quest6A", "Debto1.Quest6B", "Debto1.Quest6C", "Debto1.Quest7"],
                "0.00",
            ),
            "Debto1.Quest8A": "",
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
            "check3": "/no",
            "4b": "",
            "10": "30.00",
            "13": "20.00",
            "14": "",
            "16": "",
            "Other 16": "",
            "Other 21": "",
            "21": "",
            "4": "850.00",
            "22a": "1280.00",
            "22c": "1280.00",
            "23a": "1750.00",
            "23b": "1280.00",
            "23c": "470.00",
        },
        # Her rows (§9.6). No secured debt: D's last-page total prints 0.00, as 106Sum 2. The
        # hospital's two address lines print joined on E/F's one street line.
        "schedule_d": {"undefined_24": "0.00"},
        "schedule_e_f": {
            "check1": "/no",
            "Total_6a": "0.00",
            "Total_6b": "0.00",
            "Total_6c": "0.00",
            "Total_6d": "0.00",
            "Total_6e": "0.00",
            "Creditors Name_6": "Keelson Loan Servicing",
            "Student loans_6": "/On",
            "Creditors Name_7": "Lakemont University Hospital",
            "Street_7": "70 Demo Plaza, Lakemont Health Patient Accounts",
            "Creditors Name_12": "Wicker Demo Recovery LLC",
            "Referenced line 5.1": "4.2",
        },
        "schedule_g": {"Company Name 2.1": "Damen Demo Flats LLC"},
        "schedule_h": {"check1": "/no"},
        "list_of_creditors": {
            "creditor1.0.0": "Keelson Loan Servicing 60 Demo Way Wilkes-Barre, PA 18773",
            "creditor1.0.1": "Lakemont University Hospital 70 Demo Plaza Lakemont Health Patient Accounts Chicago, IL 60612",
            "creditor1.0.2": "Wicker Demo Recovery LLC 80 Demo Ct Oak Brook, IL 60523",
            "creditor1.0.3": "Damen Demo Flats LLC 90 Demo St Chicago, IL 60622",
            "creditor1.0.4": "",
        },
    },
    # His driving is a business on line 5 and 8a since 3e2 (§11).
    "andres": {
        "form_101": {"Debtor1.County": "Kane", "Check Box7": "/Pay in installments"},
        # Schedule A/B totals, hand-worked: 5 = 0 (leased Corolla) + 4,300 (his half of the Fit); 15 = 1,200+400+300; 36 = 60+412+85; 45 = 310+150 = 460; 62 = 63 = 4,300+1,900+557+460
        "schedule_a_b": {
            "undefined_26": "4300.00",
            "15 amount": "1900.00",
            "undefined_124": "557.00",
            "undefined_143": "460.00",  # line 45: he answers line 37 Yes
            "undefined_154": "",  # line 52: he answers line 46 No, which skips it
            "undefined_159": "0.00",
            "undefined_163": "460.00",  # line 59 copies line 45
            "undefined_164": "0.00",  # line 60 prints under line 46's No
            "undefined_166": "7217.00",
            "undefined_167": "7217.00",
            # His lines, PS:1311-1320: the leased car at a typed $0, the co-owned car with both
            # values, his share savings on 17.3 (3b spec §10), and Part 5.
            **_own_car("Toyota", "Corolla Hybrid", "2024", "61000", "0.00"),
            "Other information": "Leased",
            "If you own or have more than one describe here": "Honda",
            "1_2": "Fit",
            "2_2": "2017",
            "Approximate mileage_2": "96000",
            "undefined_16": "8600.00",
            "undefined_17": "4300.00",
            "Who has interest in property 5": "/One of Debtors and another",
            "6 description": "Beds, couch, table, kitchen things",
            "6 description amount": "1200.00",
            "7 description": "Phone, TV",
            "7 description amount": "400.00",
            "11 description": "Clothes",
            "11 description amount": "300.00",
            "Check 16": "/yes",
            "16 Cash amount": "60.00",
            "Check 17": "/yes",
            "17.1 Checking account": "Harborline Bank",
            "17.1 Checking amount": "412.00",
            "17.2 Checking account": "",
            "17.3 Checking account": "Prairie Line Credit Union",
            "17.3 Checking amount": "85.00",
            "check 37": "/yes",
            "check 38": "/yes",
            "38 Accounts receivable or commissions already earned": (
                "Driving payouts already earned, not yet paid by the apps"
            ),
            "undefined_125": "310.00",
            "check 40": "/yes",
            "40 Machinery fixtures equipment and tools of your trade": (
                "Insulated delivery bags, phone mount, dash camera"
            ),
            "undefined_127": "150.00",
            **_no_lines("check 39", "check 41", "check 42", "check 43", "check 44"),
            **_no_lines("check 46", "check 53"),
            "check 47": "",  # under line 46's No
        },
        "form_106sum": {
            "1a": "0.00",
            "1b": "7217.00",
            "1c": "7217.00",
            "2": "7800.00",
            "3a": "2140.00",
            "3b": "23160.00",
            "3c": "33100.00",
            "4": "3370.00",
            "5": "3034.00",
            "9b": "2140.00",
            "9g": "2140.00",
        },
        "form_122a1": {
            "CheckBox1": "/No Abuse",
            "Debto1.Quest5A": "4200.00",
            "Debto1.Quest5B": "830.00",
            "Debto1.Quest5C": "3370.00",
            **dict.fromkeys(
                ["Debto1.Quest6A", "Debto1.Quest6B", "Debto1.Quest6C", "Debto1.Quest7"],
                "0.00",
            ),
            "Debto1.Quest8A": "",
            LINE_10_SOURCE: "",
            "Debto1.Quest10A": "0.00",
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
            "Amount 8a Debtor 1": "3370.00",
            "Amount 8f Debtor 1": "0.00",
            "Other income 8h": "",
            "Amount 8h Debtor 1": "0.00",
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
            "check3": "/no",
            "4b": "15.00",
            "10": "40.00",
            "13": "30.00",
            "14": "20.00",
            "16": "150.00",
            "Other 16": "2026 estimated income tax",
            "Other 21": "",
            "4": "1150.00",
            "17b": "",
            "22a": "3034.00",
            "22c": "3034.00",
            "23a": "3370.00",
            "23b": "3034.00",
            "23c": "336.00",
        },
        # His rows (§9.6). The Fit is co-owned with his brother, so Columns B and C stay blank.
        # E/F's own pages hold his first six unsecured debts in creditor order (S20); 4.7-4.9
        # print on a copy of page 4 (test_andres_e_f_continues_on_a_copy_of_page_4).
        "schedule_d": {
            "Creditors Name": "Copperline Auto Finance",
            "check 2": "/One of debtors and another",
            "undefined": "7800.00",
            "undefined_2": "",
            "undefined_3": "",
            "undefined_24": "7800.00",
        },
        "schedule_e_f": {
            "check1": "/yes",
            "Total_6a": "0.00",
            "Total_6b": "2140.00",
            "Total_6c": "0.00",
            "Total_6d": "0.00",
            "Total_6e": "2140.00",
            "Creditors Name": "Internal Revenue Service",
            "account number": "",
            "Street": "Centralized Insolvency Operation",
            "1": "P.O. Box 7346",
            "2": "Philadelphia",
            "3": "PA",
            "4": "19101-7346",
            "Date debt was incurred": "tax year 2025",
            "undefined": "2140.00",
            "undefined_2": "",
            "undefined_3": "",
            "Taxes and ceratin other debts you owe the government": "/On",
            "undefined_4.4": "4.4",
            "undefined_4.5": "4.5",
            "undefined_4.6": "4.6",
            "Creditors Name_6": "Bright Signal Wireless",
            "Creditors Name_7": "Calumet Ridge Medical Center",
            "Creditors Name_8": "Driveline Tire & Auto",
            "Creditors Name_9": "Hollowmere Residential LLC",
            "Disputed_9": "/On",
            "Creditors Name_10": "Illinois State Toll Highway Authority",
            "Creditors Name_11": "Northgate Card Services",
            "Creditors Name_12": "Ashgrove Recovery Group",
            "Referenced line 5.1": "4.2",
        },
        "schedule_g": {
            "Company Name 2.1": "Northlight Auto Leasing",
            "Company Name 2.2": "Fox Run Property Management",
        },
        "schedule_h": {
            "Codebtor Name 3.1": "Mateo Kettleby",
            "check schedule line D 3.1": "/yes",
            "Schedule line D 3.1": "2.1",
            "check schedule line E/F 3.1": "",
            "check schedule line G 3.1": "",
        },
        "list_of_creditors": {
            "creditor1.0.0": "Copperline Auto Finance PO Box 48210 Schaumburg, IL 60168",
            "creditor1.0.1": "Internal Revenue Service Centralized Insolvency Operation P.O. Box 7346 Philadelphia, PA 19101-7346",
            "creditor1.0.2": "Bright Signal Wireless PO Box 77031 Dallas, TX 75377",
            "creditor1.0.3": "Calumet Ridge Medical Center 2500 Ridge Crest Pkwy Aurora, IL 60504",
            "creditor1.0.4": "Driveline Tire & Auto 1650 N Farnsworth Ave Aurora, IL 60505",
            "creditor2.0.0": "Hollowmere Residential LLC 88 Ridgeway Ct Naperville, IL 60540",
            "creditor2.0.1": "Illinois State Toll Highway Authority 2700 Ogden Ave Downers Grove, IL 60515",
            "creditor2.0.2": "Northgate Card Services PO Box 60917 Phoenix, AZ 85082",
            "creditor2.0.3": "Prairie Line Credit Union 310 E Galena Blvd Aurora, IL 60505",
            "creditor2.0.4": "Sablewood Bank PO Box 15022 Columbus, OH 43218",
            "creditor1.0.5.0": "Tallowfield Lending Co. PO Box 31544 Wilmington, DE 19850",
            "creditor1.0.5.1": "Ashgrove Recovery Group 900 Commerce Dr Ste 210 Oak Brook, IL 60523",
            "creditor1.0.5.2": "Northlight Auto Leasing PO Box 92650 Itasca, IL 60143",
            "creditor1.0.5.3": "Fox Run Property Management 2200 W Indian Trail Aurora, IL 60506",
            "creditor1.0.5.4": "Mateo Kettleby 377 Douglas Ave Elgin, IL 60120",
            "creditor1.0.5.5": "",
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


@pytest.mark.slow
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
    elif re.fullmatch(r"\d+\.\d\d", expected):  # every widget prints it; a blank one is no amount
        assert {_amount(s) for s in shown} == {
            _amount(expected)
        }, f"wrong_value: prints {sorted(shown)}, expected {expected}"
    else:  # every widget prints it
        assert shown == {expected}, f"wrong_value: prints {sorted(shown)}, expected {expected}"


@pytest.mark.django_db
def test_andres_statement_prints_his_driving_business():
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", "--reset", persona="andres", verbosity=0)
    session = IntakeSession.objects.filter(user__username="demo_andres").latest("id")
    parts = build_parts("schedule_i", session)

    (sheet,) = read_sheets(
        PDFFormFiller().fill("schedule_i", parts), sheet_spec(parts["parts"][-1])
    )

    assert sheet.rows == (
        (
            "1",
            "Debtor 1",
            "Business: Rideshare and delivery driving",
            "4200.00",
            "830.00",
            "3370.00",
        ),
    )


@pytest.mark.slow
@pytest.mark.django_db
def test_andres_e_f_continues_on_a_copy_of_page_4():
    # His nine unsecured debts outrun E/F Part 2's six rows: 4.7-4.9 print on a copy of page 4,
    # each numbered in its entry box, and page 6 becomes the seventh page of seven (R18).
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", "--reset", persona="andres", verbosity=0)
    session = IntakeSession.objects.filter(user__username="demo_andres").latest("id")
    document = build_parts("schedule_e_f", session)

    drawn = read_drawn(
        "schedule_e_f", PDFFormFiller().fill("schedule_e_f", document), document["parts"]
    )

    on_copy = {w.full_name: w.value for w in drawn if w.copy == 1 and not w.state}
    rows = {
        "undefined_4.4": "4.7",
        "Creditors Name_9": "Prairie Line Credit Union",
        "undefined_4.5": "4.8",
        "Creditors Name_10": "Sablewood Bank",
        "undefined_4.6": "4.9",
        "Creditors Name_11": "Tallowfield Lending Co.",
    }
    assert {name: on_copy[name] for name in rows} == rows
    # He answered Yes to offset on Prairie Line, where his savings are: the copy ticks it Yes
    assert {w.state for w in drawn if w.copy == 1 and w.full_name == "check11"} - {"/Off"} == {
        "/yes"
    }
    # The copy is the fifth page, so page 5 becomes the sixth.
    assert on_copy["fill_27.1.4"] == "5"
    page_5 = {w.full_name: w.value for w in drawn if w.page == 5 and w.copy is None}
    assert page_5["fill_27.1.6"] == "6"
    page_6 = {w.full_name: w.value for w in drawn if w.page == 6 and w.copy is None}
    assert (page_6["fill_27.1.8"], page_6["fill_27.1.7"]) == ("7", "7")
