#!/usr/bin/env python
"""Django management script without database."""
import os
import sys
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Minimal settings for makemigrations
if not settings.configured:
    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parent
    
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'apps.intake',
            'apps.districts',
            'apps.eligibility',
            'apps.forms',
        ],
        SECRET_KEY='temp-key-for-migration-gen',
        USE_TZ=True,
    )

django.setup()

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
