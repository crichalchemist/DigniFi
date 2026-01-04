"""
Django settings for DigniFi project.

CRITICAL: This platform must respect UPL (Unauthorized Practice of Law) boundaries.
All development must ensure we provide legal INFORMATION, never legal ADVICE.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/
"""

import os
from pathlib import Path
from datetime import timedelta
import environ
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Create logs directory
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True, parents=True)

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR.parent, ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", default="")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

if not SECRET_KEY and not DEBUG:
    raise ImproperlyConfigured("The DJANGO_SECRET_KEY environment variable is not set.")

if not SECRET_KEY and DEBUG:
    SECRET_KEY = "django-insecure-CHANGE-ME-IN-PRODUCTION"

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "encrypted_model_fields",
    # DigniFi apps (in priority order)
    "apps.users",
    "apps.audit",
    "apps.districts",
    "apps.intake",
    "apps.eligibility",
    "apps.forms",
    "apps.content",
    "apps.case_management",
    "apps.credit_counseling",
    "apps.documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # Must be before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditLoggingMiddleware",  # Custom UPL audit logging
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://dignifi:dignifi@localhost:5432/dignifi_dev"
    )
}

# Custom User Model
AUTH_USER_MODEL = "users.User"

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},  # Stronger password requirement
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"  # Illinois/Chicago timezone
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files (user-uploaded content)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "EXCEPTION_HANDLER": "apps.audit.exception_handler.upl_aware_exception_handler",
}

# JWT Settings

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),  # Short-lived for security
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS Settings
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"]
)
CORS_ALLOW_CREDENTIALS = True

# Field Encryption (for PII: SSN, income data, etc.)
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

if not FIELD_ENCRYPTION_KEY:
    raise ImproperlyConfigured(
        "The FIELD_ENCRYPTION_KEY environment variable is not set."
    )

# DigniFi-Specific Settings

# Default district for MVP
DEFAULT_DISTRICT = env("DEFAULT_DISTRICT", default="ilnd")

# UPL Compliance Settings
UPL_AUDIT_ENABLED = True
UPL_PROHIBITED_PHRASES = [
    "you should file",
    "i recommend",
    "you should choose",
    "my advice is",
    "you need to file",
    "based on your situation, file",
]

# Plain Language Settings
PLAIN_LANGUAGE_TARGET_GRADE_LEVEL = 7  # 6th-8th grade (Flesch-Kincaid)
PLAIN_LANGUAGE_VALIDATION_ENABLED = DEBUG  # Enable in dev for warnings

# Trauma-Informed Design Settings
TRAUMA_INFORMED_MODE = True
TRAUMA_SENSITIVE_TERMS = {
    "debt": "amounts owed",
    "debtor": "filer",
    "failure": "situation",
    "default": "missed payment",
}

# PDF Generation Settings
PDF_GENERATION_BACKEND = "PyPDF2"  # Alternative: 'pdfrw'
PDF_FORMS_DIRECTORY = BASE_DIR.parent / "data" / "forms" / "pdfs"
PDF_OUTPUT_DIRECTORY = MEDIA_ROOT / "generated_forms"

# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "audit": {
            "format": "[AUDIT] {asctime} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "audit_file": {
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "audit.log"),
            "formatter": "audit",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "dignifi.audit": {
            "handlers": ["audit_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "dignifi.upl": {
            "handlers": ["audit_file", "console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Security Settings (will be strengthened in production)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

# Data Retention Policy (for GDPR/privacy compliance)
DATA_RETENTION_DAYS = 2555  # 7 years (bankruptcy discharge timeline)
AUDIT_LOG_RETENTION_DAYS = 3650  # 10 years (legal compliance)
