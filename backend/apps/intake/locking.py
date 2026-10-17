"""One save at a time on an intake session (DIG-188)."""

from .models import IntakeSession


def lock_session(session_id: int) -> IntakeSession:
    """Lock the session's row until the transaction ends, and return the session as stored.

    Every write to a session's intake data calls this first, inside the same
    ``transaction.atomic()`` block as the write, so a second save of the same session waits
    for the first to commit and then reads what it stored. Postgres refuses it outside a
    transaction; sqlite ignores it, so only test_session_lock.py on Postgres proves it.
    """
    return IntakeSession.objects.select_for_update().get(pk=session_id)
