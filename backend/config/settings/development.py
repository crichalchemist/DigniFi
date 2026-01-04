from .base import *

DEBUG = True

# Development-specific settings
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow all hosts in development
ALLOWED_HOSTS = ["*"]

# Django Extensions (optional)
if "django_extensions" not in INSTALLED_APPS:
    INSTALLED_APPS += ["django_extensions"]
