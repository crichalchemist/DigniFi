"""Shared test fixtures for the forms app."""

import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.field_index import load_index
from apps.forms.models import GeneratedForm
from apps.forms.schema import load_schema
from apps.forms.services.widgets import template_widgets
from apps.intake.household import ANSWER_KEYS, SPOUSE_KEY
from apps.intake.models import (
    DebtorInfo,
    Household,
    IncomeInfo,
    IntakeSession,
    SOFACreditorPayment,
    SOFAReport,
)
from apps.intake.tests.builders import answer_household

User = get_user_model()

# A slot's boxes, (box, label, the SOFA creditor payment attribute it prints).
_NAME = ("Creditor's name", "creditor_name")
_AMOUNT = ("Amount of claim", "total_paid")
# Schedule D Part 1's rows as (page, boxes), each a creditor's name and a Column A amount:
# 2.1 and 2.2 on page 1, then page 2's three rows, which the filer numbers from 2.3.
_D_PART_1 = [
    (1, [("Creditors Name", *_NAME), ("undefined", *_AMOUNT)]),
    (1, [("Creditors Name_2", *_NAME), ("undefined_5", *_AMOUNT)]),
    (2, [("Creditors Name_3", *_NAME), ("undefined_10", *_AMOUNT)]),
    (2, [("Creditors Name_4", *_NAME), ("undefined_14", *_AMOUNT)]),
    (2, [("Creditors Name_5", *_NAME), ("undefined_20", *_AMOUNT)]),
]
# Schedule D Part 2's six entries on page 3, the template's last page: each a name.
_D_PART_2 = [
    (3, [(box, *_NAME)]) for box in ["Name", "Name_2", "Name_3", "Name_4", "Name_5", "Name_6"]
]
_D_PAGE_NUMBERS = [
    {"page": 1, "this": None, "of": "fill_27.0"},
    {"page": 2, "this": "fill_27.1.0", "of": "fill_27.1.1"},
    {"page": 3, "this": "fill_28.1.1", "of": "fill_28.1.2"},
]
# Schedule E/F's continued pages: Part 1 on page 2, Part 2 on page 4, Part 3 on page 5.
_EF_PAGE_NUMBERS = [
    {"page": 1, "this": None, "of": "fill_27.0"},
    {"page": 2, "this": "fill_27.1.0", "of": "fill_27.1.1"},
    {"page": 3, "this": "fill_27.1.2", "of": "fill_27.1.3"},
    {"page": 4, "this": "fill_27.1.4", "of": "fill_27.1.5"},
    {"page": 5, "this": "fill_27.1.6", "of": "fill_27.1.7"},
    {"page": 6, "this": "fill_27.1.8", "of": "fill_27.1.7"},
]
_EF_GROUPS = {
    "ef_part_1": (2, ["Creditors Name_3", "Creditors Name_4", "Creditors Name_5"]),
    "ef_part_2": (4, ["Creditors Name_9", "Creditors Name_10", "Creditors Name_11"]),
    "ef_part_3": (5, ["Creditors Name_12", "Creditors Name_13", "Creditors Name_14"]),
}
# Schedule A/B line 3's four vehicles, 3.1 and 3.2 on page 2, 3.3 and 3.4 on page 3: each a
# make and the current value of the portion the filer owns, kept as a SOFA creditor payment's
# name and amount (R19: no new list source in 3a2).
_MAKE = ("Make", "creditor_name")
_VALUE = ("Current value of the portion you own", "total_paid")
_AB_LINE_3 = [
    (2, [("3 1", *_MAKE), ("undefined_15", *_VALUE)]),
    (2, [("If you own or have more than one describe here", *_MAKE), ("undefined_17", *_VALUE)]),
    (3, [("1_3", *_MAKE), ("undefined_19", *_VALUE)]),
    (3, [("1_4", *_MAKE), ("undefined_21", *_VALUE)]),
]
_AB_SHEET = {
    "title": "Official Form 106A/B, Schedule A/B: Property",
    "columns": [
        {"label": "Make", "binding": "sofa.creditor_payments[].creditor_name", "width": 300},
        {
            "label": "Current value of the portion you own",
            "binding": "sofa.creditor_payments[].total_paid",
            "width": 168,
        },
    ],
}
_D_SHEET = {
    "title": "Official Form 106D, Schedule D: Creditors Who Have Claims Secured by Property",
    "columns": [
        {
            "label": "Creditor's name",
            "binding": "sofa.creditor_payments[].creditor_name",
            "width": 300,
        },
        {
            "label": "Amount of claim",
            "binding": "sofa.creditor_payments[].total_paid",
            "width": 168,
        },
    ],
}
_CREDITORS = [
    "Ashby Auto Credit",
    "Birchfield Lending",
    "Corvale Finance",
    "Dunmere Savings",
    "Elsworth Credit",
    "Fenwick Motor Credit",
    "Glasmere Loans",
    "Halcott Finance",
    "Ivyrock Credit",
]


@pytest.fixture
def index_copy(tmp_path, settings):
    """
    A writable copy of the field index. edit(template, change) rewrites one
    template's rows. The caches built from an index are cleared before and after,
    so the copy never poisons, or is poisoned by, the real index.
    """
    for path in Path(django_settings.FORM_INDEX_DIRECTORY).glob("*.index.json"):
        shutil.copy(path, tmp_path)
    settings.FORM_INDEX_DIRECTORY = tmp_path
    load_index.cache_clear()
    template_widgets.cache_clear()

    def edit(template_filename, change):
        path = tmp_path / f"{Path(template_filename).stem}.index.json"
        rows = json.loads(path.read_text())
        change(rows)
        path.write_text(json.dumps(rows))

    yield edit
    load_index.cache_clear()
    template_widgets.cache_clear()


def _with_group(tmp_path, settings, form_type, group, rows, declaration, page_numbers=None):
    """
    Copy the real schemas into tmp_path, unless an earlier fixture of the test has, and point
    FORM_SCHEMAS_DIRECTORY there, with a synthetic repeat group on form_type: row n's slot is
    rows[n - 1], (page, boxes), each box bound to that SOFA creditor payment's attribute; the
    group's declaration is `declaration`, beside any group added before. Returns the
    schemas directory.
    """
    schemas = tmp_path / "schemas"
    if not schemas.exists():
        shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, schemas)
    path = schemas / f"{form_type}.json"
    schema = json.loads(path.read_text())
    # A production claims group would collide with the synthetic one: start from the bare form.
    claims = [f for f in schema["fields"] if (f.get("binding") or "").startswith("claims.")]
    if claims:
        named = {f["repeat"] for f in claims if f.get("repeat")}
        schema["fields"] = [f for f in schema["fields"] if f not in claims]
        for name in named:
            schema.get("groups", {}).pop(name, None)
        schema.pop("page_numbers", None)
    for row, (page, boxes) in enumerate(rows, start=1):
        for pdf_field, label, attr in boxes:
            schema["fields"].append(
                {
                    "pdf_field": pdf_field,
                    "type": "text",
                    "source": "asked",
                    "page": page,
                    "label": label,
                    "required": False,
                    "conditional_on": None,
                    "value": None,
                    "rule": None,
                    "ingest_key": None,
                    "binding": f"sofa.creditor_payments[].{attr}",
                    "repeat": group,
                    "repeat_capacity": len(rows),
                    "row": row,
                    "legal_review": False,
                }
            )
    schema.setdefault("groups", {})[group] = declaration
    if page_numbers is not None:
        schema["page_numbers"] = page_numbers
    path.write_text(json.dumps(schema))
    settings.FORM_SCHEMAS_DIRECTORY = schemas
    return schemas


@pytest.fixture
def schedule_d_with_copies(tmp_path, settings):
    """
    A copy of the real schemas whose Schedule D has a synthetic repeat group (3a2 spec
    §5.4, R18, R19): Part 1's five rows, each a SOFA creditor payment's name and amount,
    continued on copies of page 2, numbered "2.{n}", with the page-number boxes of pages
    1 to 3. Yields the schemas directory. The schema cache is cleared before and after,
    so the synthetic Schedule D never poisons, or is poisoned by, the real one.
    """
    declaration = {
        "extra_page": 2,
        "number": "2.{n}",
        "number_boxes": {
            "3": "undefined_12",
            "4": "undefined_19@2:T37",
            "5": "undefined_19@2:T63",
        },
    }
    schemas = _with_group(
        tmp_path, settings, "schedule_d", "d_part_1", _D_PART_1, declaration, _D_PAGE_NUMBERS
    )
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


@pytest.fixture
def schedule_d_part_2_with_copies(tmp_path, settings):
    """
    As schedule_d_with_copies, but Schedule D's one synthetic group is Part 2's six
    entries on page 3, continued on copies of that page, the template's last, as C, G
    and H continue theirs, with the page-number boxes of pages 1 to 3. Yields the schemas directory.
    """
    schemas = _with_group(
        tmp_path,
        settings,
        "schedule_d",
        "d_part_2",
        _D_PART_2,
        {"extra_page": 3},
        _D_PAGE_NUMBERS,
    )
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


@pytest.fixture
def schedule_d_with_two_groups(tmp_path, settings):
    """
    Schedule D with both Parts continued on copies, as 3c5 declares them (3c spec §9.1): Part 1
    on copies of page 2, Part 2 on copies of page 3, with the form's page-number boxes.
    """
    _with_group(tmp_path, settings, "schedule_d", "d_part_2", _D_PART_2, {"extra_page": 3})
    schemas = _with_group(
        tmp_path, settings, "schedule_d", "d_part_1", _D_PART_1, {"extra_page": 2}, _D_PAGE_NUMBERS
    )
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


@pytest.fixture
def schedule_d_with_totals(tmp_path, settings):
    """
    Schedule D's Part 1 with its total boxes (3c spec §5.3): the amounts add up in undefined_9 on
    page 1, undefined_23 on page 2 and each copy of it, and undefined_24 on the last. Production
    Schedule D's group is stripped by _with_group, so these totals are the box's only writer.
    """
    declaration = {
        "extra_page": 2,
        "totals": {
            "column": "sofa.creditor_payments[].total_paid",
            "page_boxes": {"1": "undefined_9", "2": "undefined_23"},
            "last_page_box": "undefined_24",
        },
    }
    schemas = _with_group(tmp_path, settings, "schedule_d", "d_part_1", _D_PART_1, declaration)
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


@pytest.fixture
def schedule_g_numbered(tmp_path, settings):
    """
    Schedule G's rows as 3c5 declares them (3c spec §9.1): five on page 1, whose numbers the
    form prints, and eight on page 2, each a SOFA creditor payment's name with its number in
    the box after the printed "2.", continued on copies of page 2.
    """
    rows = [(1 if n <= 5 else 2, [(f"Company Name 2.{n}", *_NAME)]) for n in range(1, 14)]
    declaration = {
        "extra_page": 2,
        "number": "{n}",
        "number_boxes": {str(n): f"fill 2.{n}" for n in range(6, 14)},
    }
    schemas = _with_group(tmp_path, settings, "schedule_g", "g", rows, declaration)
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


@pytest.fixture
def schedule_d_with_totals_and_part_2(tmp_path, settings, schedule_d_with_totals):
    """
    Schedule D as 3c5 declares it (3c spec §5.3, §9.1): Part 1's total boxes, Part 2 on copies of
    page 3, and the form's page-number boxes.
    """
    declaration = {"extra_page": 3}
    schemas = _with_group(
        tmp_path, settings, "schedule_d", "d_part_2", _D_PART_2, declaration, _D_PAGE_NUMBERS
    )
    load_schema.cache_clear()
    yield schemas


@pytest.fixture
def schedule_e_f_with_copies(tmp_path, settings):
    """
    write(capacities, reverse): Schedule E/F with three groups on the real names of pages 2, 4
    and 5, the nth holding capacities[n] rows of that page's three, every row a SOFA creditor
    payment's name, continued on copies of its page, with the form's page-number boxes. With
    reverse, the schema declares the groups last page first.
    """

    def write(capacities=(3, 3, 3), reverse=False):
        schemas = None
        declared = list(zip(_EF_GROUPS.items(), capacities, strict=True))
        for (group, (page, names)), capacity in reversed(declared) if reverse else declared:
            rows = [(page, [(box, *_NAME)]) for box in names[:capacity]]
            schemas = _with_group(
                tmp_path,
                settings,
                "schedule_e_f",
                group,
                rows,
                {"extra_page": page},
                _EF_PAGE_NUMBERS,
            )
        load_schema.cache_clear()
        return schemas

    yield write
    load_schema.cache_clear()


@pytest.fixture
def schedule_a_b_with_sheet(tmp_path, settings):
    """
    A copy of the real schemas whose Schedule A/B has a synthetic repeat group (3a2 spec
    §5.4, R18, R19): line 3's four vehicles, each a make and its value, continued on an
    attached sheet under those two columns, its rows numbered "3.{n}". The real schema's
    repeat groups are dropped first, so this one is the form's only group. Yields the schemas
    directory, cleared from the schema cache before and after, as schedule_d_with_copies.
    """
    schemas = tmp_path / "schemas"
    if not schemas.exists():
        shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, schemas)
    path = schemas / "schedule_a_b.json"
    schema = json.loads(path.read_text())
    schema["fields"] = [f for f in schema["fields"] if f["repeat"] is None]
    schema["groups"] = {}
    path.write_text(json.dumps(schema))
    declaration = {"number": "3.{n}", "sheet": _AB_SHEET}
    schemas = _with_group(tmp_path, settings, "schedule_a_b", "ab_line_3", _AB_LINE_3, declaration)
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


@pytest.fixture
def schedule_d_with_a_copy_and_a_sheet(tmp_path, settings):
    """
    Schedule D with both continuations (R56): Part 2's six entries on copies of page 3, the
    template's last, and Part 1's five rows on an attached sheet, numbered "2.{n}" under a
    name column and an amount column. Yields the schemas directory.
    """
    _with_group(tmp_path, settings, "schedule_d", "d_part_2", _D_PART_2, {"extra_page": 3})
    declaration = {"number": "2.{n}", "sheet": _D_SHEET}
    schemas = _with_group(tmp_path, settings, "schedule_d", "d_part_1", _D_PART_1, declaration)
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


# Schedule J line 2's rows a to e: the dependent's relationship, age and "Does dependent
# live with you?" boxes.
_J_LINE_2 = [(f"Dependant Relation 2{x}", f"Dependant age 2{x}", f"check2{x}") for x in "abcde"]
_J_SHEET = {
    "title": "Official Form 106J, Schedule J: Your Expenses, line 2",
    "columns": [
        {"label": "Relationship", "binding": "household.dependents[].relationship", "width": 220},
        {"label": "Age", "binding": "household.dependents[].age", "width": 80},
        {
            "label": "Lives with you",
            "binding": "household.dependents[].lives_with_you",
            "width": 168,
        },
    ],
}


@pytest.fixture
def schedule_j_with_dependents(tmp_path, settings):
    """
    A copy of the real schemas whose Schedule J has line 2 as 3e1 declares it (spec §10.3):
    rows a to e, each a household dependent's relationship, age and "lives with you?"
    boxes, continued on an attached sheet, its rows numbered "2.{n}". Any binding of those
    boxes in the real schema is dropped first. Yields the schemas directory, cleared from
    the schema cache before and after, as schedule_d_with_copies.
    """
    schemas = tmp_path / "schemas"
    if not schemas.exists():
        shutil.copytree(django_settings.FORM_SCHEMAS_DIRECTORY, schemas)
    path = schemas / "schedule_j.json"
    schema = json.loads(path.read_text())
    boxes = {box for row in _J_LINE_2 for box in row}
    schema["fields"] = [f for f in schema["fields"] if f["pdf_field"] not in boxes]
    for row, (relationship, age, lives_with_you) in enumerate(_J_LINE_2, start=1):
        for pdf_field, kind, attr, choices in [
            (relationship, "text", "relationship", None),
            (age, "text", "age", None),
            (lives_with_you, "checkbox", "lives_with_you", {"yes": "/yes", "no": "/no"}),
        ]:
            slot = {
                "pdf_field": pdf_field,
                "type": kind,
                "source": "asked",
                "page": 1,
                "label": pdf_field,
                "required": False,
                "conditional_on": None,
                "value": None,
                "rule": None,
                "ingest_key": None,
                "binding": f"household.dependents[].{attr}",
                "repeat": "j_line_2",
                "repeat_capacity": 5,
                "row": row,
                "legal_review": False,
            }
            if choices is not None:
                slot["choices"] = choices
            schema["fields"].append(slot)
    schema.setdefault("groups", {})["j_line_2"] = {"number": "2.{n}", "sheet": _J_SHEET}
    path.write_text(json.dumps(schema))
    settings.FORM_SCHEMAS_DIRECTORY = schemas
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


@pytest.fixture
def household_list():
    """
    store(session, *rows): the session's household list, each row (relationship, age,
    lives_with_you, claimed_or_supported[, spouse_is_dependent]); returns the session read
    afresh from the database.
    """

    def store(session, *rows):
        household, _ = Household.objects.get_or_create(session=session)
        # A row without the spouse question stops at claimed_or_supported.
        keys = (*ANSWER_KEYS, SPOUSE_KEY)
        household.store_members([dict(zip(keys, row, strict=False)) for row in rows])
        household.save()
        return IntakeSession.objects.get(pk=session.pk)

    return store


@pytest.fixture
def creditor_payments():
    """
    add(session, count, names=None): that many SOFA creditor payments, the nth named
    names[n - 1] (by default a firm), each at n00.00.
    """

    def add(session, count, names=None):
        names = names or _CREDITORS
        report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
        return [
            SOFACreditorPayment.objects.create(
                report=report,
                creditor_name=names[n - 1] if n <= len(names) else f"Creditor {n}",
                total_paid=Decimal(f"{n}00.00"),
            )
            for n in range(1, count + 1)
        ]

    return add


@pytest.fixture
def api_client_authed(db):
    user = User.objects.create_user(username="testuser", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def generated_form_factory(db, api_client_authed):
    def _make(status="generated"):
        user = User.objects.filter(username="testuser").first()
        district = District.objects.filter(code="ilnd").first()
        if not district:
            # The real ILND data: preparing a form works the means test out against its median.
            call_command("loaddata", "ilnd_2025_data", verbosity=0)
            district = District.objects.get(code="ilnd")
        session = IntakeSession.objects.create(
            user=user, district=district, status="completed", current_step=9
        )
        DebtorInfo.objects.create(
            session=session,
            first_name="Maria",
            last_name="Torres",
            ssn="900-11-0001",  # IRS-reserved range: synthetic
            date_of_birth=date(1988, 6, 15),
            street_address="2145 W Division St",
            city="Chicago",
            state="IL",
            zip_code="60622",
        )
        IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("2800.00"))
        answer_household(session)
        return GeneratedForm.objects.create(
            session=session,
            form_type="form_121",
            status=status,
            generated_by=user,
        )

    return _make
