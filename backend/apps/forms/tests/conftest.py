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
from apps.intake.models import (
    DebtorInfo,
    IncomeInfo,
    IntakeSession,
    SOFACreditorPayment,
    SOFAReport,
)

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


def _with_group(tmp_path, settings, form_type, group, rows, declaration):
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
        "page_numbers": [
            {"page": 1, "this": None, "of": "fill_27.0"},
            {"page": 2, "this": "fill_27.1.0", "of": "fill_27.1.1"},
            {"page": 3, "this": "fill_28.1.1", "of": "fill_28.1.2"},
        ],
    }
    schemas = _with_group(tmp_path, settings, "schedule_d", "d_part_1", _D_PART_1, declaration)
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


@pytest.fixture
def schedule_d_part_2_with_copies(tmp_path, settings):
    """
    As schedule_d_with_copies, but Schedule D's one synthetic group is Part 2's six
    entries on page 3, continued on copies of that page, the template's last, as C, G
    and H continue theirs. Yields the schemas directory.
    """
    schemas = _with_group(
        tmp_path, settings, "schedule_d", "d_part_2", _D_PART_2, {"extra_page": 3}
    )
    load_schema.cache_clear()
    yield schemas
    load_schema.cache_clear()


@pytest.fixture
def schedule_a_b_with_sheet(tmp_path, settings):
    """
    A copy of the real schemas whose Schedule A/B has a synthetic repeat group (3a2 spec
    §5.4, R18, R19): line 3's four vehicles, each a make and its value, continued on an
    attached sheet under those two columns, its rows numbered "3.{n}". Yields the schemas
    directory, cleared from the schema cache before and after, as schedule_d_with_copies.
    """
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
            user=user, district=district, status="completed", current_step=6
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
        return GeneratedForm.objects.create(
            session=session,
            form_type="form_121",
            status=status,
            generated_by=user,
        )

    return _make
