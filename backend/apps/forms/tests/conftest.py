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
from apps.forms.services.widgets import template_widgets
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


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
