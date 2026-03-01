import django
from django.conf import settings

# Configure Django settings for pytest
django_settings_module = 'config.settings.test'

# Standalone manual test scripts — not pytest tests.
collect_ignore = [
    "test_fee_waiver_manual.py",
    "test_debt_classification.py",
    "test_schedule_ab_logic.py",
]


def pytest_configure():
    settings.DJANGO_SETTINGS_MODULE = django_settings_module
    django.setup()
