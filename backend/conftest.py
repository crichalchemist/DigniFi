from datetime import date

import django
import pytest
from django.conf import settings

# Configure Django settings for pytest
django_settings_module = "config.settings.test"

# Standalone manual test scripts — not pytest tests.
collect_ignore = [
    "test_debt_classification.py",
    "test_schedule_ab_logic.py",
    # A settings module, not tests: its name matches python_files, and importing it during
    # collection would point the running settings' default database at DATABASE_URL.
    "config/settings/test_postgres.py",
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


@pytest.fixture
def poverty_2026(db):
    # The 2026 HHS poverty guideline, which 0005_poverty_guideline_2026 loads. A transactional
    # test's teardown empties every table, the migrated row included, so a test that needs the
    # row after one asks for this fixture. Imported here: this module loads before django.setup().
    from apps.districts.models import PovertyGuideline

    row, _ = PovertyGuideline.objects.get_or_create(
        effective_date=date(2026, 1, 15),
        defaults={
            "first_person": 15960,
            "each_additional": 5680,
            "valid_through": date(2027, 1, 31),
            "source_url": (
                "https://www.federalregister.gov/documents/2026/01/15/2026-00755/"
                "annual-update-of-the-hhs-poverty-guidelines"
            ),
        },
    )
    return row
