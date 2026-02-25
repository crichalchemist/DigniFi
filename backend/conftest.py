import django
from django.conf import settings

# Configure Django settings for pytest
django_settings_module = 'config.settings.test'


def pytest_configure():
    settings.DJANGO_SETTINGS_MODULE = django_settings_module
    django.setup()
