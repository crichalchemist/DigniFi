from .base import *  # noqa: F403, F401

DEBUG = False

# ── Allowed hosts ──────────────────────────────────────────────────────
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost"])

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

# ── Static files (served by nginx in production) ─────────────────────
STATIC_URL = "/static/"

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
