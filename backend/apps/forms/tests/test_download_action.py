"""
Download fills the official template: the filer's current answers until a form
is filed, and exactly what was filed afterwards (spec §5.5).
"""

import json
import logging
from unittest.mock import patch

from django.urls import reverse

from apps.forms.services.fill_resolver import RepeatOverflow
from apps.forms.tests.pdf_readback import read_drawn


def _download(client, form):
    return client.get(reverse("generated-forms-download", kwargs={"pk": form.pk}))


def _printed(response, full_name):
    """What the downloaded Form 121 prints in each widget of that name."""
    return {w.value for w in read_drawn("form_121", response.content) if w.full_name == full_name}


def _rename_filer(form, first_name):
    debtor = form.session.debtor_info
    debtor.first_name = first_name
    debtor.save()


def test_download_streams_the_filled_form(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    response = _download(api_client_authed, form)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == 'attachment; filename="form_121.pdf"'
    assert _printed(response, "Debtor1.First name") == {"Maria"}


def test_download_marks_a_generated_form_downloaded(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    _download(api_client_authed, form)
    form.refresh_from_db()
    assert form.status == "downloaded"


def test_unfiled_form_prints_the_filers_current_answers(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="downloaded")
    form.field_values = json.dumps({"Debtor1.First name": "Maria"})
    form.save()
    _rename_filer(form, "Marisol")

    response = _download(api_client_authed, form)

    assert _printed(response, "Debtor1.First name") == {"Marisol"}
    form.refresh_from_db()
    assert json.loads(form.field_values)["Debtor1.First name"] == "Marisol"


def test_filed_form_prints_what_was_filed(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="filed")
    form.field_values = json.dumps({"Debtor1.First name": "Maria"})
    form.save()
    _rename_filer(form, "Marisol")

    response = _download(api_client_authed, form)

    assert _printed(response, "Debtor1.First name") == {"Maria"}
    form.refresh_from_db()
    assert form.status == "filed"


def test_filed_form_without_a_snapshot_is_resolved_once_and_kept(
    api_client_authed, generated_form_factory
):
    form = generated_form_factory(status="filed")  # filed before snapshots existed

    response = _download(api_client_authed, form)

    assert _printed(response, "Debtor1.First name") == {"Maria"}
    form.refresh_from_db()
    assert json.loads(form.field_values)["Debtor1.First name"] == "Maria"


def test_a_letter_the_form_cannot_print_refuses_the_download(
    api_client_authed, generated_form_factory, caplog
):
    # An invented surname: ą is outside the court form's font, which would print "?".
    form = generated_form_factory(status="generated")
    _rename_filer(form, "Wąsowicz")

    with caplog.at_level(logging.DEBUG):
        response = _download(api_client_authed, form)

    assert response.status_code == 422
    assert response.data == {
        "form_type": "form_121",
        "error": "The court form can't print the letter “ą” in “Debtor 1 first name”. "
        "Change it to a letter without the mark.",
        "step": "debtor_info",
    }
    assert "ą" not in caplog.text  # the letter, and so the name that holds it
    assert "Debtor 1 first name" not in caplog.text


def test_form_no_longer_in_the_packet_is_refused(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    form.form_type = "form_103b"  # no fee waiver application for this session
    form.save()

    response = _download(api_client_authed, form)

    assert response.status_code == 422
    assert response.data["error"] == (
        "This form isn't part of your packet, based on the answers you've given."
    )


def test_missing_data_is_a_422_with_its_reason(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    form.session.debtor_info.delete()

    response = _download(api_client_authed, form)

    assert response.status_code == 422
    assert "name and address" in response.data["error"]


def test_too_many_rows_is_a_422(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    overflow = RepeatOverflow("form_121", "rows", capacity=3, actual=4)
    with patch("apps.forms.views.build_field_values", side_effect=overflow):
        response = _download(api_client_authed, form)
    assert response.status_code == 422
    # No repeat group name or capacity: the filer reads this beside the form's label.
    assert response.data == {
        "form_type": "form_121",
        "error": "You have more entries than this form has room for. The extra entries "
        "need a continuation page, which this app can't make yet.",
    }


def test_unexpected_failure_logs_only_its_type(api_client_authed, generated_form_factory, caplog):
    form = generated_form_factory(status="generated")
    with patch("apps.forms.views.build_field_values", side_effect=ValueError("900-11-0001")):
        response = _download(api_client_authed, form)
    assert response.status_code == 500
    assert "900-11-0001" not in caplog.text
    assert "ValueError" in caplog.text
