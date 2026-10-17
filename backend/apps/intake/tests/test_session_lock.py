"""One save at a time on an intake session (DIG-188).

Business intent: a filer can send two saves of one list at once (Continue pressed twice),
an upload can write a scanned debt while the filer saves, and Complete can run while a save
or an upload's findings arrive. Every write to a session's intake data locks the session
first, so they run one after the other: a new row is stored once, a scanned debt waits for
the save in progress instead of slipping into it, and an edit or a pay stub that lands
while Complete runs still sends the filer back to press Complete again.

select_for_update does nothing on sqlite, so these tests run only on Postgres:
    DJANGO_SETTINGS_MODULE=config.settings.test_postgres pytest -m postgres
Each request runs on its own thread and database connection, as two browser requests do.
A request "waits" when Postgres reports its connection waiting on a lock.
"""

import threading
import time
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.conf import settings as django_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, transaction
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents import views as document_views
from apps.documents.models import (
    DocumentType,
    IngestedAggregate,
    OCRResult,
    OCRStatus,
    UploadedDocument,
)
from apps.documents.services.processor import ExtractionResult
from apps.intake import views as intake_views
from apps.intake.locking import lock_session
from apps.intake.models import (
    AssetInfo,
    Codebtor,
    DebtInfo,
    DebtorInfo,
    ExecutoryContract,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
)
from apps.users.models import User

# CI runs these with config.settings.test_postgres. If those settings ever reach anything
# but Postgres, stop the run here instead of letting every test skip quietly.
if (
    django_settings.SETTINGS_MODULE == "config.settings.test_postgres"
    and connection.vendor != "postgresql"
):
    raise RuntimeError(f"config.settings.test_postgres reached {connection.vendor}, not Postgres")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason=(
            "needs Postgres: select_for_update does nothing on sqlite; "
            "CI runs it with config.settings.test_postgres"
        ),
    ),
    pytest.mark.django_db(transaction=True),
]

# Seconds a test waits for a request. Under test_postgres's lock_timeout (10 s), so a
# deadlock fails the test here instead of hanging the run.
WAIT = 5

NEW_DEBT = {
    "creditor_name": "Prairie Card Services",
    "debt_type": "credit_card",
    "amount_owed": "75.00",
}
NEW_CONTRACT = {
    "counterparty_name": "Oak Street Apartments",
    "contract_type": "lease",
    "description": "",
}


@pytest.fixture
def ready(transactional_db):
    """A filer's intake with everything Complete checks, still in progress."""
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(
        user=user, district=district, status="in_progress", current_step=8
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        number_of_dependents=0,
        monthly_gross_wages=Decimal("3000.00"),
    )
    ExpenseInfo.objects.create(session=session)
    return user, session


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _session_url(session, action=""):
    return f"/api/intake/sessions/{session.pk}/{action}"


def _on_its_own_thread(request):
    """Start request() on a thread with its own database connection.

    Returns the thread and a dict that gets the response, or the exception it raised.
    """
    outcome = {}

    def run():
        try:
            outcome["response"] = request()
        except BaseException as exc:
            outcome["error"] = exc
        finally:
            connection.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, outcome


def _waits_on_a_lock(thread):
    """True once a connection to the test database waits on a lock while `thread` runs;
    False when the thread ends first or WAIT runs out."""
    deadline = time.monotonic() + WAIT
    while thread.is_alive() and time.monotonic() < deadline:
        with connection.cursor() as cursor:
            # Postgres reads pg_stat_activity once per transaction; drop that copy.
            cursor.execute("SELECT pg_stat_clear_snapshot()")
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity"
                " WHERE datname = current_database() AND wait_event_type = 'Lock'"
            )
            if cursor.fetchone()[0]:
                return True
        time.sleep(0.02)
    return False


def _finished(thread, outcome):
    thread.join(WAIT)
    assert not thread.is_alive(), "the request never finished: a save deadlocked"
    if "error" in outcome:
        raise outcome["error"]
    return outcome["response"]


def test_two_saves_of_the_same_new_contract_store_it_once(ready):
    # Continue on the Contracts step sends the whole list. Pressed twice, both saves carry
    # the lease the filer just typed, which has no id yet. Each save reads the stored rows
    # before it writes; this pauses the first save after its writes, before it commits.
    user, session = ready
    first_saved = threading.Event()
    go_on = threading.Event()
    save_rows = intake_views._save_rows_by_id

    def first_save_pauses_before_commit(*args, **kwargs):
        save_rows(*args, **kwargs)
        if not first_saved.is_set():
            first_saved.set()
            go_on.wait(WAIT)

    def save():
        return _client(user).put(_session_url(session, "contracts/"), [NEW_CONTRACT], format="json")

    with patch.object(intake_views, "_save_rows_by_id", first_save_pauses_before_commit):
        first, first_outcome = _on_its_own_thread(save)
        assert first_saved.wait(WAIT)
        second, second_outcome = _on_its_own_thread(save)
        second_waited = _waits_on_a_lock(second)
        go_on.set()
        assert _finished(first, first_outcome).status_code == 200
        assert _finished(second, second_outcome).status_code == 200

    assert ExecutoryContract.objects.filter(session=session).count() == 1
    assert second_waited, "the second save ran while the first was still writing"


@contextmanager
def _the_hosted_model_pauses(reading_of_the_upload):
    """While active, the hosted model's read of an upload sets `reading`, waits for `go_on`
    and returns `reading_of_the_upload`. Yields (reading, go_on)."""
    reading = threading.Event()
    go_on = threading.Event()

    def read(*args):
        reading.set()
        go_on.wait(WAIT)
        return reading_of_the_upload

    run_processing = document_views._run_processing

    def run_processing_then_close(doc_id):
        try:
            run_processing(doc_id)
        finally:
            connection.close()  # the executor's thread opens its own connection

    with (
        patch.object(document_views, "_get_processor") as get_processor,
        patch.object(document_views, "_run_processing", run_processing_then_close),
    ):
        get_processor.return_value.process.side_effect = read
        yield reading, go_on


@contextmanager
def _complete_pauses_in_its_checks():
    """While active, Complete sets `checking` once it holds the lock and is checking the
    intake, then waits for `go_on`. Yields (checking, go_on)."""
    checking = threading.Event()
    go_on = threading.Event()
    income = intake_views.current_monthly_income

    def check_income(income_info):
        checking.set()
        go_on.wait(WAIT)
        return income(income_info)

    with patch.object(intake_views, "current_monthly_income", check_income):
        yield checking, go_on


def _upload(user, session, document_type, filename):
    return _client(user).post(
        "/api/documents/upload/",
        {
            "file": SimpleUploadedFile(filename, b"%PDF-1.4 scan", content_type="application/pdf"),
            "document_type": document_type,
            "session_id": session.pk,
        },
        format="multipart",
    )


def test_an_uploads_scanned_debt_waits_for_a_save_in_progress_then_is_stored(
    ready, settings, tmp_path
):
    # The draft is written by the upload's worker thread while the request thread waits for
    # it, so only the worker may take the lock: a lock held by the request thread, or held
    # across the call to the hosted model, would stop the save below from starting.
    user, session = ready
    settings.MEDIA_ROOT = tmp_path
    bill = ExtractionResult(
        fields={
            "creditor_name": "Lakeshore Medical Billing",
            "amount_owed": "1284.50",
            "creditor_type": "medical",
        },
        confidence={"overall": 88},
        detected_type=DocumentType.CREDITOR_BILL,
    )

    with _the_hosted_model_pauses(bill) as (reading, go_on):
        uploading, outcome = _on_its_own_thread(
            lambda: _upload(user, session, DocumentType.CREDITOR_BILL, "bill.pdf")
        )
        assert reading.wait(WAIT)
        with transaction.atomic():
            lock_session(session.pk)  # the filer's save starts while the bill is being read
            go_on.set()
            findings_waited = _waits_on_a_lock(uploading)
            stored_during_the_save = DebtInfo.objects.filter(session=session).exists()
        response = _finished(uploading, outcome)

    assert not stored_during_the_save
    assert findings_waited, "the scanned debt was written while the save was in progress"

    assert response.status_code == 202
    draft = DebtInfo.objects.get(session=session)
    assert (draft.creditor_name, draft.is_draft) == ("Lakeshore Medical Billing", True)
    assert OCRResult.objects.get(document_id=response.json()["id"]).status == OCRStatus.COMPLETED


def test_an_edit_made_while_complete_runs_reopens_the_intake(ready):
    user, session = ready

    with _complete_pauses_in_its_checks() as (checking, go_on):
        completing, completed = _on_its_own_thread(
            lambda: _client(user).post(_session_url(session, "complete/"))
        )
        assert checking.wait(WAIT)
        editing, edited = _on_its_own_thread(
            lambda: _client(user).patch(_session_url(session), {"debts": [NEW_DEBT]}, format="json")
        )
        edit_waited = _waits_on_a_lock(editing)
        go_on.set()
        assert _finished(completing, completed).status_code == 200
        assert _finished(editing, edited).status_code == 200

    assert IntakeSession.objects.get(pk=session.pk).status == "in_progress"
    assert edit_waited, "the edit saved while Complete was checking"


def test_a_pay_stub_read_while_complete_runs_reopens_the_intake(ready, settings, tmp_path):
    # A pay stub's findings reopen the intake before they write anything that waits on the
    # session row, so only the worker's own lock keeps them from landing inside Complete.
    user, session = ready
    settings.MEDIA_ROOT = tmp_path
    pay_stub = ExtractionResult(
        fields={
            "employer_name": "Lakeview Logistics",
            "gross_pay": "1000.00",
            "pay_period_start": "2026-01-01",
            "pay_period_end": "2026-01-14",
        },
        confidence={"overall": 90},
        detected_type=DocumentType.PAY_STUB,
    )

    with (
        _the_hosted_model_pauses(pay_stub) as (reading, read_on),
        _complete_pauses_in_its_checks() as (checking, complete_on),
    ):
        uploading, uploaded = _on_its_own_thread(
            lambda: _upload(user, session, DocumentType.PAY_STUB, "stub.pdf")
        )
        assert reading.wait(WAIT)
        completing, completed = _on_its_own_thread(
            lambda: _client(user).post(_session_url(session, "complete/"))
        )
        assert checking.wait(WAIT)
        read_on.set()
        findings_waited = _waits_on_a_lock(uploading)
        complete_on.set()
        assert _finished(completing, completed).status_code == 200
        assert _finished(uploading, uploaded).status_code == 202

    assert IntakeSession.objects.get(pk=session.pk).status == "in_progress"
    employer = IngestedAggregate.objects.get(session=session, ingest_key="paystub.employer_name")
    assert employer.value == "Lakeview Logistics"
    assert findings_waited, "the pay stub's findings were written while Complete was checking"


def test_a_save_keeps_the_step_a_continue_stored_while_it_waited(ready):
    # A session save writes the whole session row back. Read before the lock, it would put
    # back the step and status it saw, over a Continue that committed meanwhile.
    user, session = ready

    with transaction.atomic():
        lock_session(session.pk)
        IntakeSession.objects.filter(pk=session.pk).update(current_step=5)  # a Continue
        saving, outcome = _on_its_own_thread(
            lambda: _client(user).patch(_session_url(session), {"debts": [NEW_DEBT]}, format="json")
        )
        save_waited = _waits_on_a_lock(saving)
    response = _finished(saving, outcome)

    assert response.status_code == 200
    assert IntakeSession.objects.get(pk=session.pk).current_step == 5
    assert save_waited, "the save ran while the Continue was in progress"


@pytest.mark.parametrize(
    "endpoint, kind, model", [("assets", "asset", AssetInfo), ("debts", "debt", DebtInfo)]
)
def test_a_row_deleted_while_its_update_waited_is_not_found_and_stays_deleted(
    ready, endpoint, kind, model
):
    # The Assets or Amounts Owed step's save deletes a row the filer removed while a
    # per-item update of that row waits for the lock.
    user, session = ready
    row = _rows(session)[kind]

    with transaction.atomic():
        lock_session(session.pk)
        model.objects.filter(pk=row.pk).delete()  # the step's save drops the row
        updating, outcome = _on_its_own_thread(
            lambda: _client(user).patch(
                f"/api/intake/{endpoint}/{row.pk}/", {"amount_owed": "10.00"}, format="json"
            )
        )
        update_waited = _waits_on_a_lock(updating)
    response = _finished(updating, outcome)

    assert response.status_code == 404
    assert not model.objects.filter(pk=row.pk).exists()
    assert update_waited, "the update ran while the save was in progress"


def test_a_row_moved_to_another_session_while_its_update_waited_is_not_found(ready):
    # The update locked only the session the row was on; writing it now would change the
    # other session without that session's lock.
    user, session = ready
    other = IntakeSession.objects.create(user=user, district=session.district)
    debt = _rows(session)["debt"]

    with transaction.atomic():
        lock_session(session.pk)
        DebtInfo.objects.filter(pk=debt.pk).update(session=other)  # a move by another request
        updating, outcome = _on_its_own_thread(
            lambda: _client(user).patch(
                f"/api/intake/debts/{debt.pk}/", {"amount_owed": "10.00"}, format="json"
            )
        )
        update_waited = _waits_on_a_lock(updating)
    response = _finished(updating, outcome)

    assert response.status_code == 404
    moved = DebtInfo.objects.get(pk=debt.pk)
    assert (moved.session_id, moved.amount_owed) == (other.pk, Decimal("1000.00"))
    assert update_waited, "the update ran while the save was in progress"


def _rows(session):
    """One stored row of each kind a write below changes."""
    bill = UploadedDocument.objects.create(
        session=session,
        uploaded_by=session.user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename="bill.pdf",
        file_size=100,
        mime_type="application/pdf",
        file="documents/bill.pdf",
    )
    OCRResult.objects.create(
        document=bill,
        status=OCRStatus.COMPLETED,
        extracted_data='{"creditor_name": "Lakeshore Medical"}',
        confidence_scores={},
        overall_confidence=80,
    )
    return {
        "contract": ExecutoryContract.objects.create(
            session=session, counterparty_name="Oak Street Apartments", contract_type="lease"
        ),
        "codebtor": Codebtor.objects.create(
            session=session, name="Sam Doe", relationship="relative"
        ),
        "asset": AssetInfo.objects.create(
            session=session,
            asset_type="vehicle",
            description="Car",
            current_value=Decimal("5000.00"),
            amount_owed=Decimal("0.00"),
        ),
        "debt": DebtInfo.objects.create(
            session=session,
            creditor_name="Prairie Card Services",
            debt_type="credit_card",
            amount_owed=Decimal("1000.00"),
        ),
        "bill": bill,
    }


# Every intake-data write: (method, path, body, expected status).
WRITES = {
    "session PATCH": lambda s, r: ("patch", _session_url(s), {"debts": [NEW_DEBT]}, 200),
    "session PUT": lambda s, r: ("put", _session_url(s), {"district": s.district_id}, 200),
    "Continue": lambda s, r: ("post", _session_url(s, "update_step/"), {"current_step": 3}, 200),
    "Complete": lambda s, r: ("post", _session_url(s, "complete/"), {}, 200),
    "contracts PUT": lambda s, r: (
        "put",
        _session_url(s, "contracts/"),
        [{"counterparty_name": "Metro Gym", "contract_type": "contract", "description": ""}],
        200,
    ),
    "contract POST": lambda s, r: (
        "post",
        _session_url(s, "contracts/"),
        {"counterparty_name": "Metro Gym", "contract_type": "contract", "description": ""},
        201,
    ),
    "contract DELETE": lambda s, r: (
        "delete",
        _session_url(s, f"contracts/{r['contract'].pk}/"),
        None,
        204,
    ),
    "codebtors PUT": lambda s, r: (
        "put",
        _session_url(s, "codebtors/"),
        [{"name": "Ana Ruiz", "relationship": "friend"}],
        200,
    ),
    "codebtor POST": lambda s, r: (
        "post",
        _session_url(s, "codebtors/"),
        {"name": "Ana Ruiz", "relationship": "friend"},
        201,
    ),
    "codebtor DELETE": lambda s, r: (
        "delete",
        _session_url(s, f"codebtors/{r['codebtor'].pk}/"),
        None,
        204,
    ),
    "asset POST": lambda s, r: (
        "post",
        "/api/intake/assets/",
        {
            "session": s.pk,
            "asset_type": "vehicle",
            "description": "Second car",
            "current_value": "2000.00",
            "amount_owed": "0",
        },
        201,
    ),
    "asset PATCH": lambda s, r: (
        "patch",
        f"/api/intake/assets/{r['asset'].pk}/",
        {"description": "Paid-off car"},
        200,
    ),
    "asset DELETE": lambda s, r: ("delete", f"/api/intake/assets/{r['asset'].pk}/", None, 204),
    "debt POST": lambda s, r: (
        "post",
        "/api/intake/debts/",
        {
            "session": s.pk,
            "creditor_name": "Lakeshore Medical Billing",
            "debt_type": "medical",
            "priority_classification": "unsecured",
            "amount_owed": "120.00",
            "monthly_payment": "0.00",
        },
        201,
    ),
    "debt PATCH": lambda s, r: (
        "patch",
        f"/api/intake/debts/{r['debt'].pk}/",
        {"amount_owed": "900.00"},
        200,
    ),
    "debt DELETE": lambda s, r: ("delete", f"/api/intake/debts/{r['debt'].pk}/", None, 204),
    "scanned bill correction": lambda s, r: (
        "post",
        f"/api/documents/{r['bill'].pk}/validate/",
        {"fields": {"creditor_name": "Lakeshore Medical Billing"}},
        200,
    ),
}


@pytest.mark.parametrize("write", WRITES)
def test_every_intake_write_waits_for_a_save_in_progress(ready, write):
    # Also proves each write runs inside its own transaction: Postgres refuses a lock
    # taken outside one, which sqlite never does.
    user, session = ready
    method, url, body, expected = WRITES[write](session, _rows(session))

    def send():
        return getattr(_client(user), method)(url, body, format="json")

    with transaction.atomic():
        lock_session(session.pk)  # a save in progress
        sending, outcome = _on_its_own_thread(send)
        waited = _waits_on_a_lock(sending)
    response = _finished(sending, outcome)

    assert waited, f"{write} wrote without waiting for the save in progress"
    assert response.status_code == expected, response.content
