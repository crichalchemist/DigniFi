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
from apps.forms import views
from apps.forms.models import GeneratedForm
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.means_pair import box_1_state, stored_check_box_1
from apps.forms.tests.pdf_readback import read_drawn
from apps.forms.views import MEANS_PAIR_REFUSAL
from apps.intake.completion import EXPENSES_STEP_NEVER_SAVED
from apps.intake.models import DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_household,
    answer_means_test,
    answer_petition,
    finish_intake,
)

User = get_user_model()
LINE_16 = "Enter the amount for line 16. Enter 0 if you have none."

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
    finish_intake(session)
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

    # the tie (H43) refuses before the page's gap: above the median, 122A-2 has no row
    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a1", "error": MEANS_PAIR_REFUSAL},
    )
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("generated", stored)
    download = api_client.get(f"/api/forms/{row.pk}/download/")
    assert (download.status_code, download.data["error"]) == (422, LINE_16)


def _a_generated_pair_whose_expenses_row_is_gone(api_client, session):
    """Both pair rows generated above the median, then the Expenses row deleted (a gate gap)."""
    _set_wages(session, "9000.00")
    answer_means_test(session)
    first = _generate(api_client, session, "form_122a1")
    second = _generate(api_client, session, "form_122a2")
    ExpenseInfo.objects.filter(session=session).delete()
    return first, second


@pytest.mark.django_db
def test_a_gate_gap_comes_before_the_means_pair_tie(api_client, session_with_debtor):
    # Before 4a the same call was refused with the tie sentence: this pins which refusal is first.
    session = session_with_debtor
    first, second = _a_generated_pair_whose_expenses_row_is_gone(api_client, session)

    resp = _mark_filed(api_client, first)

    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a1", "error": EXPENSES_STEP_NEVER_SAVED, "step": "expense_info"},
    )
    for row in (first, second):
        row.refresh_from_db()
    assert (first.status, second.status) == ("generated", "generated")


@pytest.mark.django_db
def test_a_gate_gap_refuses_the_pair_action_and_marks_neither(api_client, session_with_debtor):
    # The per-row Mark as Filed is refused by the tie whatever _prepare says, so the pair action
    # is the path that would mark both rows past a gate.
    session = session_with_debtor
    first, second = _a_generated_pair_whose_expenses_row_is_gone(api_client, session)

    resp = api_client.post("/api/forms/mark_pair_filed/", {"session_id": session.pk}, format="json")

    assert (resp.status_code, resp.data) == (
        422,
        {"error": EXPENSES_STEP_NEVER_SAVED, "step": "expense_info"},
    )
    for row in (first, second):
        row.refresh_from_db()
    assert (first.status, second.status) == ("generated", "generated")


@pytest.mark.django_db
def test_a_stale_122a1_row_with_its_partner_filed_is_held_by_the_pages_gap(
    api_client, session_with_debtor
):
    session = session_with_debtor
    row = _generate(api_client, session)
    stored = row.field_values
    _set_wages(session, "9000.00")
    GeneratedForm.objects.create(session=session, form_type="form_122a2", status="filed")

    resp = _mark_filed(api_client, row)

    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a1", "error": LINE_16, "page": "/means-test"},
    )
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("generated", stored)


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
def test_a_stale_122a2_row_under_a_supp_outcome_is_not_in_the_packet(
    api_client, session_with_debtor
):
    session = session_with_debtor
    _set_wages(session, "9000.00")
    answer_means_test(session)
    row = _generate(api_client, session, "form_122a2")
    stored = row.field_values
    answer_petition(session, debt_nature="business")  # a Supp outcome: 122A-2 leaves the packet

    resp = _mark_filed(api_client, row)

    assert resp.status_code == 422
    assert resp.data == {
        "form_type": "form_122a2",
        "error": "This form isn't part of your packet, based on the answers you've given.",
    }
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("generated", stored)


@pytest.mark.django_db
def test_a_122a1_filed_with_box_1_still_downloads_as_stored_above_the_median(
    api_client, session_with_debtor
):
    session = session_with_debtor
    row = _generate(api_client, session)
    assert _mark_filed(api_client, row).status_code == 200
    row.refresh_from_db()
    document = json.loads(row.field_values)
    assert stored_check_box_1(row) == box_1_state()
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

    assert (resp.status_code, resp.data["error"]) == (422, LINE_16)


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

    # the tie (H43) refuses before the page's gap: 122A-1 has no row
    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a2", "error": MEANS_PAIR_REFUSAL},
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
    assert resp.data == {
        "form_type": "form_122a1",
        "error": "The court form can't print the letter “ą” in “Debtor name”. "
        "Change it to a letter without the mark.",
        "step": "debtor_info",
    }
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


@pytest.mark.django_db
def test_a_form_downloaded_while_marking_is_not_reported_filed(api_client, session_with_debtor):
    # The conditional update loses to the other write, and the reply says what the row now is.
    session = session_with_debtor
    row = _generate(api_client, session)
    intervening = json.dumps(
        {"version": 2, "parts": [{"kind": "form", "values": {"Quest11": "1234.00"}}]}
    )
    check = PDFFormFiller.check

    def check_then_download_elsewhere(filler, form_type, values):
        result = check(filler, form_type, values)
        GeneratedForm.objects.filter(pk=row.pk).update(
            status="downloaded", field_values=intervening
        )
        return result

    with patch.object(PDFFormFiller, "check", check_then_download_elsewhere):
        resp = _mark_filed(api_client, row)

    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "downloaded"
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("downloaded", intervening)


# Form 122A-1Supp says to submit it with the signed Form 122A-1 (D4): under one of its outcomes the
# Supp is 122A-1's partner, on either side of the median, and the two are marked filed together.
SUPP_FORMS = ("form_122a1", "form_122a1_supp")
BOX_3 = "/Does not apply"


def _as_stored(session):
    """Each means form's row as the database holds it, so a refusal is shown to have written
    nothing."""
    return {
        r.form_type: (r.status, r.field_values, r.updated_at)
        for r in GeneratedForm.objects.filter(session=session, form_type__in=views.MEANS_FORMS)
    }


@pytest.mark.parametrize("wages", ["3000.00", "9000.00"], ids=["below", "above"])
@pytest.mark.django_db
def test_marking_122a1_alone_is_refused_while_the_supp_is_unfiled(
    api_client, session_with_debtor, wages
):
    session = session_with_debtor
    _set_wages(session, wages)
    answer_petition(session, debt_nature="business")
    row = _generate(api_client, session, "form_122a1")
    _generate(api_client, session, "form_122a1_supp")
    before = _as_stored(session)

    resp = _mark_filed(api_client, row)

    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a1", "error": views.MEANS_SUPP_PAIR_REFUSAL},
    )
    assert _as_stored(session) == before
    assert set(before) == set(SUPP_FORMS)


@pytest.mark.django_db
def test_marking_the_supp_alone_is_refused_while_122a1_is_unfiled(api_client, session_with_debtor):
    session = session_with_debtor
    _set_wages(session, "9000.00")
    answer_petition(session, debt_nature="business")
    row = _generate(api_client, session, "form_122a1_supp")
    before = _as_stored(session)

    resp = _mark_filed(api_client, row)

    assert (resp.status_code, resp.data) == (
        422,
        {"form_type": "form_122a1_supp", "error": views.MEANS_SUPP_PAIR_REFUSAL},
    )
    assert _as_stored(session) == before
    assert set(before) == {"form_122a1_supp"}


@pytest.mark.django_db
def test_a_filed_122a1_with_box_3_shows_no_mismatch(api_client, session_with_debtor):
    # The mismatch notice is for a filed 122A-1 that doesn't tick box 2 while 122A-2 applies; a line
    # 3 exclusion files 122A-1 with box 3 beside the Supp, and 122A-2 isn't in the packet.
    session = session_with_debtor
    _set_wages(session, "9000.00")
    answer_petition(
        session,
        debt_nature="consumer",
        disabled_veteran="no",
        reservist="yes",
        called_to_duty="yes",
        duty_category="1",
    )

    marked = api_client.post(
        "/api/forms/mark_pair_filed/", {"session_id": session.pk}, format="json"
    )

    assert marked.status_code == 200, marked.data
    row = GeneratedForm.objects.get(session=session, form_type="form_122a1")
    assert stored_check_box_1(row) == BOX_3
    assert _listed(api_client, session)["form_122a1"]["stored_box_2"] is False
    forms = api_client.get("/api/forms/packet/", {"session": session.pk}).data["form_types"]
    assert "form_122a2" not in forms
    assert "form_122a1_supp" in forms


@pytest.mark.django_db
def test_the_supp_is_marked_filed_alone_once_122a1_is_filed(api_client, session_with_debtor):
    # D11's route: 122A-1 was filed first (box 1, before the filer's answers changed), so the
    # Supp's partner is already filed and nothing holds the Supp back from being filed alone.
    session = session_with_debtor
    _set_wages(session, "9000.00")
    answer_petition(session, debt_nature="business")
    GeneratedForm.objects.create(session=session, form_type="form_122a1", status="filed")
    row = _generate(api_client, session, "form_122a1_supp")

    resp = _mark_filed(api_client, row)

    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "filed"
    row.refresh_from_db()
    assert row.status == "filed"


@pytest.mark.django_db
def test_a_supp_row_outside_the_packet_cant_be_marked_filed(api_client, session_with_debtor):
    # A consumer filer below the median has no Supp outcome, so a Supp row left from earlier
    # answers is not in the packet and is refused rather than filed.
    session = session_with_debtor
    answer_petition(session, debt_nature="consumer", disabled_veteran="no", reservist="no")
    stored = json.dumps({"version": 2, "parts": [{"kind": "form", "values": {}}]})
    row = GeneratedForm.objects.create(
        session=session, form_type="form_122a1_supp", status="generated", field_values=stored
    )

    resp = _mark_filed(api_client, row)

    assert (resp.status_code, resp.data) == (
        422,
        {
            "form_type": "form_122a1_supp",
            "error": "This form isn't part of your packet, based on the answers you've given.",
        },
    )
    row.refresh_from_db()
    assert (row.status, row.field_values) == ("generated", stored)
