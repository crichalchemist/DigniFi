"""
A 122A-1 or 122A-2 marked filed is the one worked out when it was marked filed, so a copy made
before the hold can't leave DigniFi around it.
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.models import GeneratedForm
from apps.forms.registry import FORM_122A2_NOT_ASKED
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household

User = get_user_model()

BOX_2 = "/Presumption of abuse applies"
BOX_1 = "/No Abuse"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testfiler", email="filer@example.com", password="testpass123"
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def district(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


@pytest.fixture
def session_with_debtor(user, district):
    session = IntakeSession.objects.create(user=user, district=district, status="completed")
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("3000.00")
    )
    answer_household(session)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        middle_name="",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


def _set_wages(session, wages):
    income = session.income_info
    income.monthly_gross_wages = Decimal(wages)
    income.save()


def _generate(api_client, session, form_type="form_122a1"):
    resp = api_client.post(
        "/api/forms/generate/", {"session_id": session.pk, "form_type": form_type}, format="json"
    )
    assert resp.status_code == 200, resp.data
    return GeneratedForm.objects.get(session=session, form_type=form_type)


def _mark_filed(api_client, row):
    return api_client.post(f"/api/forms/{row.pk}/mark_filed/")


def _printed(form_type, pdf, document):
    """What a drawn PDF prints, widget by widget (each draw has its own trailer /ID)."""
    return sorted(
        (w.full_name, w.copy, w.value) for w in read_drawn(form_type, pdf, document["parts"])
    )


def _listed(api_client, session):
    resp = api_client.get("/api/forms/", {"session": session.pk})
    assert resp.status_code == 200, resp.data
    return {r["form_type"]: r for r in resp.data["results"]}


@pytest.mark.django_db
def test_a_stale_122a1_row_cant_be_filed_around_the_hold(api_client, session_with_debtor):
    session = session_with_debtor
    row = _generate(api_client, session)
    stored = row.field_values
    _set_wages(session, "9000.00")

    resp = _mark_filed(api_client, row)

    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a1", "error": FORM_122A2_NOT_ASKED},
    )
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("generated", stored)
    download = api_client.get(f"/api/forms/{row.pk}/download/")
    assert (download.status_code, download.data["error"]) == (422, FORM_122A2_NOT_ASKED)


@pytest.mark.django_db
def test_marking_the_pair_filed_keeps_the_document_worked_out_then(api_client, session_with_debtor):
    session = session_with_debtor
    row = _generate(api_client, session)
    _set_wages(session, "3500.00")  # still below the median, and no Generate

    resp = _mark_filed(api_client, row)

    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "filed"
    row.refresh_from_db()
    document = json.loads(row.field_values)
    assert document["parts"][0]["values"]["Quest11"] == "3500.00"
    assert row.status == "filed"
    download = api_client.get(f"/api/forms/{row.pk}/download/")
    assert download.status_code == 200
    drawn_now = PDFFormFiller().fill("form_122a1", document)
    assert _printed("form_122a1", download.content, document) == _printed(
        "form_122a1", drawn_now, document
    )


@pytest.mark.django_db
def test_marking_another_form_filed_is_unchanged(api_client, session_with_debtor):
    session = session_with_debtor
    row = _generate(api_client, session, "form_101")
    session.status = "in_progress"
    session.save()

    resp = _mark_filed(api_client, row)

    assert resp.status_code == 200, resp.data
    row.refresh_from_db()
    assert row.status == "filed"


@pytest.mark.django_db
def test_marking_an_already_filed_122a1_filed_again_keeps_what_it_was_filed_with(
    api_client, session_with_debtor
):
    session = session_with_debtor
    row = _generate(api_client, session)
    assert _mark_filed(api_client, row).status_code == 200
    row.refresh_from_db()
    filed_with = row.field_values
    _set_wages(session, "9000.00")

    resp = _mark_filed(api_client, row)

    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "filed"
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("filed", filed_with)


@pytest.mark.django_db
def test_a_122a1_filed_with_box_1_still_downloads_as_stored_above_the_median(
    api_client, session_with_debtor
):
    session = session_with_debtor
    row = _generate(api_client, session)
    assert _mark_filed(api_client, row).status_code == 200
    row.refresh_from_db()
    document = json.loads(row.field_values)
    _set_wages(session, "9000.00")

    download = api_client.get(f"/api/forms/{row.pk}/download/")

    assert download.status_code == 200
    assert _printed("form_122a1", download.content, document) == _printed(
        "form_122a1", PDFFormFiller().fill("form_122a1", document), document
    )
    assert _listed(api_client, session)["form_122a1"]["stored_box_2"] is False


@pytest.mark.parametrize(
    "values, box_2",
    [
        (
            {"version": 2, "parts": [{"kind": "form", "values": {"CheckBox1": BOX_2}}]},
            True,
        ),
        ({"CheckBox1": BOX_2}, True),  # a form filed before 3a2
        (
            {"version": 2, "parts": [{"kind": "form", "values": {"CheckBox1": BOX_1}}]},
            False,
        ),
        (
            {"version": 2, "parts": [{"kind": "form", "values": {"Quest11": "3000.00"}}]},
            False,
        ),  # before step 2b
        ({"version": 2, "parts": [{"kind": "copy", "page": 2, "number": 1, "values": {}}]}, False),
    ],
)
@pytest.mark.django_db
def test_the_forms_list_says_whether_a_filed_122a1_stored_box_2(
    api_client, session_with_debtor, values, box_2
):
    GeneratedForm.objects.create(
        session=session_with_debtor,
        form_type="form_122a1",
        status="filed",
        field_values=json.dumps(values),
    )

    assert _listed(api_client, session_with_debtor)["form_122a1"]["stored_box_2"] is box_2


@pytest.mark.django_db
def test_the_forms_list_says_nothing_of_box_2_for_other_rows(api_client, session_with_debtor):
    session = session_with_debtor
    stored = json.dumps({"version": 2, "parts": [{"kind": "form", "values": {"CheckBox1": BOX_2}}]})
    GeneratedForm.objects.create(session=session, form_type="form_122a1", status="filed")
    GeneratedForm.objects.create(
        session=session, form_type="form_122a2", status="filed", field_values=stored
    )
    GeneratedForm.objects.create(
        session=session, form_type="form_101", status="filed", field_values=stored
    )

    listed = _listed(api_client, session)

    assert {t: r["stored_box_2"] for t, r in listed.items()} == {
        "form_122a1": None,
        "form_122a2": None,
        "form_101": None,
    }
    unfiled = GeneratedForm.objects.get(session=session, form_type="form_122a1")
    unfiled.status = "generated"
    unfiled.field_values = stored
    unfiled.save()
    assert _listed(api_client, session)["form_122a1"]["stored_box_2"] is None


@pytest.mark.django_db
def test_a_flagged_rows_download_prints_exactly_its_stored_document(
    api_client, session_with_debtor
):
    session = session_with_debtor
    row = _generate(api_client, session)
    assert _mark_filed(api_client, row).status_code == 200
    GeneratedForm.objects.filter(pk=row.pk).update(filed_before_means_test=True)
    row.refresh_from_db()
    document = json.loads(row.field_values)
    _set_wages(session, "9000.00")

    download = api_client.get(f"/api/forms/{row.pk}/download/")

    assert download.status_code == 200
    assert _printed("form_122a1", download.content, document) == _printed(
        "form_122a1", PDFFormFiller().fill("form_122a1", document), document
    )
    assert _listed(api_client, session)["form_122a1"]["filed_before_means_test"] is True


@pytest.mark.django_db
def test_a_filed_122a2_with_nothing_stored_is_refused_by_the_hold(api_client, session_with_debtor):
    session = session_with_debtor
    _set_wages(session, "9000.00")
    row = GeneratedForm.objects.create(session=session, form_type="form_122a2", status="filed")

    resp = api_client.get(f"/api/forms/{row.pk}/download/")

    assert (resp.status_code, resp.data["error"]) == (422, FORM_122A2_NOT_ASKED)


@pytest.mark.django_db
def test_a_stale_122a2_row_cant_be_filed_around_the_hold(api_client, session_with_debtor):
    # A 122A-2 generated before 3h holds only five boxes; Mark as Filed must not file it.
    session = session_with_debtor
    _set_wages(session, "9000.00")
    stale = json.dumps({"version": 2, "parts": [{"kind": "form", "values": {"Quest11": "1.00"}}]})
    row = GeneratedForm.objects.create(
        session=session, form_type="form_122a2", status="generated", field_values=stale
    )

    resp = _mark_filed(api_client, row)

    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a2", "error": FORM_122A2_NOT_ASKED},
    )
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("generated", stale)


@pytest.mark.django_db
def test_a_letter_the_form_cannot_print_keeps_a_122a1_from_being_filed(
    api_client, session_with_debtor
):
    # Filed, its download would refuse forever with nothing to fix, so check() runs first.
    session = session_with_debtor
    row = _generate(api_client, session)
    stored = row.field_values
    debtor = session.debtor_info
    debtor.first_name = "Wąsowicz"  # ą is outside the court form's font
    debtor.save()

    resp = _mark_filed(api_client, row)

    assert resp.status_code == 422, resp.data
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("generated", stored)


@pytest.mark.django_db
def test_a_form_filed_while_marking_keeps_the_document_it_was_filed_with(
    api_client, session_with_debtor
):
    # Two presses (two tabs) can overlap: the later one must not overwrite the filed document.
    session = session_with_debtor
    row = _generate(api_client, session)
    intervening = json.dumps(
        {"version": 2, "parts": [{"kind": "form", "values": {"Quest11": "1234.00"}}]}
    )
    check = PDFFormFiller.check

    def check_then_file_elsewhere(filler, form_type, values):
        result = check(filler, form_type, values)
        GeneratedForm.objects.filter(pk=row.pk).update(status="filed", field_values=intervening)
        return result

    with patch.object(PDFFormFiller, "check", check_then_file_elsewhere):
        resp = _mark_filed(api_client, row)

    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "filed"
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("filed", intervening)
