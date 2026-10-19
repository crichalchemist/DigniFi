"""
Download fills the official template: the filer's current answers until a form
is filed, and exactly what was filed afterwards (spec §5.5).
"""

import json
import logging
from unittest.mock import ANY, patch

from django.urls import reverse

from apps.forms.services.fill_resolver import RepeatOverflow
from apps.forms.services.pdf_filler import PDFFormFiller, TemplateHasNoForm
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
    (part,) = json.loads(form.field_values)["parts"]
    assert part["values"]["Debtor1.First name"] == "Marisol"


def test_a_filed_form_downloads_exactly_what_was_filed(api_client_authed, generated_form_factory):
    form = generated_form_factory(status="generated")
    regenerate = reverse("generated-forms-regenerate", kwargs={"pk": form.pk})
    mark_filed = reverse("generated-forms-mark-filed", kwargs={"pk": form.pk})
    assert api_client_authed.post(regenerate).status_code == 200
    assert api_client_authed.post(mark_filed).status_code == 200
    form.refresh_from_db()
    filed = form.field_values
    # Spec §6's parts document: a version and the form's own part.
    assert json.loads(filed) == {"version": 2, "parts": [{"kind": "form", "values": ANY}]}
    _rename_filer(form, "Marisol")  # the filer's later edit

    response = _download(api_client_authed, form)

    assert response.status_code == 200
    assert _printed(response, "Debtor1.First name") == {"Maria"}
    form.refresh_from_db()
    assert (form.status, form.field_values) == ("filed", filed)


def test_a_form_filed_before_3a2_still_downloads(api_client_authed, generated_form_factory):
    # Filed in the shape stored before 3a2: {full name: value}, with no parts.
    form = generated_form_factory(status="filed")
    form.field_values = json.dumps({"Debtor1.First name": "Maria"})
    form.save()
    _rename_filer(form, "Marisol")

    response = _download(api_client_authed, form)

    assert _printed(response, "Debtor1.First name") == {"Maria"}
    form.refresh_from_db()
    assert form.status == "filed"


def test_a_filed_form_whose_values_cannot_print_is_refused_without_a_step_or_page(
    api_client_authed, generated_form_factory
):
    # Only a development or test database can hold one (spec §6). No step changes what was
    # filed, so the refusal names none (R46).
    form = generated_form_factory(status="filed")
    form.field_values = json.dumps(
        {"version": 2, "parts": [{"kind": "form", "values": {"Debtor1.First name": "Wąsowicz"}}]}
    )
    form.save()

    response = _download(api_client_authed, form)

    assert response.status_code == 422
    assert response.data == {
        "form_type": "form_121",
        "error": "The court form can't print the letter “ą” in “Debtor 1 first name”. "
        "Change it to a letter without the mark.",
    }


def test_filed_form_without_a_snapshot_is_resolved_once_and_kept(
    api_client_authed, generated_form_factory
):
    form = generated_form_factory(status="filed")  # filed before snapshots existed

    response = _download(api_client_authed, form)

    assert _printed(response, "Debtor1.First name") == {"Maria"}
    form.refresh_from_db()
    (part,) = json.loads(form.field_values)["parts"]
    assert part["values"]["Debtor1.First name"] == "Maria"


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
    with patch("apps.forms.views.build_parts", side_effect=overflow):
        response = _download(api_client_authed, form)
    assert response.status_code == 422
    # No repeat group name or capacity: the filer reads this beside the form's label.
    assert response.data == {
        "form_type": "form_121",
        "error": "You have more entries than this form has room for. The extra entries "
        "need a continuation page, which this app can't make yet.",
    }


def test_a_template_with_no_form_is_explained_in_plain_words(
    api_client_authed, generated_form_factory
):
    # Only drawing raises TemplateHasNoForm, so since 3a2 only Download can meet one.
    form = generated_form_factory(status="generated")
    with patch.object(PDFFormFiller, "fill", side_effect=TemplateHasNoForm("form_121")):
        response = _download(api_client_authed, form)
    assert response.status_code == 422
    assert response.data == {
        "form_type": "form_121",
        "error": "This form's blank court template can't be filled in right now.",
    }


def test_unexpected_failure_logs_only_its_type(api_client_authed, generated_form_factory, caplog):
    form = generated_form_factory(status="generated")
    with patch("apps.forms.views.build_parts", side_effect=ValueError("900-11-0001")):
        response = _download(api_client_authed, form)
    assert response.status_code == 500
    assert "900-11-0001" not in caplog.text
    assert "ValueError" in caplog.text
