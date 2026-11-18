from .base import *

# Test settings
DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES["default"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}

# A developer's repo-root .env must never turn the line 43 polish on in a test.
AI_POLISH_PROVIDER = ""
AI_POLISH_API_KEY = ""
AI_POLISH_MODEL = ""
