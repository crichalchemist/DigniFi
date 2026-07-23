from .base import *  # noqa: F403, F401

DEBUG = False

# ── Allowed hosts ──────────────────────────────────────────────────────
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost"])  # noqa: F405

# ── SSL & transport security ──────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ── Cookie security ───────────────────────────────────────────────────
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# ── Browser security headers ─────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ── Database connection pooling ───────────────────────────────────────
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=600)  # noqa: F405

# ── Static files (served by whitenoise) ──────────────────────────────
STATIC_URL = "/static/"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# ── Rate limiting (DRF throttling) ───────────────────────────────────
# Applies to all DRF views; auth endpoints get stricter limits via
# ScopedRateThrottle in their view classes.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "120/minute",
        "auth": "5/minute",  # Login/register attempts per IP
    },
}

# ── Error monitoring (Sentry) ────────────────────────────────────────
# DSN comes from the SENTRY_DSN env var — never hardcode it (public repo).
# Guarded: with no DSN, Sentry stays off (local prod runs, review apps).
SENTRY_DSN = env("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    import logging

    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    try:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            environment="production",
            # Legal-PII product — Sentry must NEVER capture personal data. These
            # deliberately override Sentry's default snippet (send_default_pii=True),
            # which would ship SSNs / account numbers / IPs to a third party.
            send_default_pii=False,
            include_local_variables=False,  # keep SSNs out of stack-trace locals
            max_request_body_size="never",  # never attach request bodies
            traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),  # noqa: F405
        )
    except Exception:
        # A malformed DSN must never take down the app it is meant to monitor.
        logging.getLogger(__name__).warning(
            "Sentry initialization failed; continuing without error monitoring.", exc_info=True
        )
