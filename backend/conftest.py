from datetime import date

import django
import pytest
from django.conf import settings

# Configure Django settings for pytest
django_settings_module = "config.settings.test"

# Standalone manual test scripts — not pytest tests.
collect_ignore = [
    "test_fee_waiver_manual.py",
    "test_debt_classification.py",
    "test_schedule_ab_logic.py",
]


def pytest_configure():
    settings.DJANGO_SETTINGS_MODULE = django_settings_module
    django.setup()


@pytest.fixture(autouse=True)
def _fill_forms_on_a_fixed_day(monkeypatch):
    # Dated tables are looked up by the day the forms are filled (3a1 spec §3.3). Pinning
    # that day keeps CI the same every month: on the real clock, the fixture's newest
    # median table would stop being in force on November 1 and every forms test would
    # refuse. Tests of the lookup itself set their own date.
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2026, 10, 16))
