from .test import *

# The tests marked postgres (apps/intake/tests/test_session_lock.py) need a real row lock,
# and select_for_update does nothing on sqlite. CI runs them against the backend job's
# Postgres service; locally, DATABASE_URL names a Postgres you can create a test database on.
DATABASES["default"] = env.db("DATABASE_URL")
# A save that deadlocks fails its test after 10 seconds instead of hanging the run.
DATABASES["default"].setdefault("OPTIONS", {})["options"] = "-c lock_timeout=10000"
