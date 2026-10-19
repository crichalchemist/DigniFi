"""
Download fills the official template: the filer's current answers until a form
is filed, and exactly what was filed afterwards (spec §5.5).
"""

import json
import logging
from unittest.mock import patch

import pymupdf
import pytest
from django.urls import reverse

from apps.forms.checks import validate_form
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller, TemplateHasNoForm
from apps.forms.tests.pdf_readback import read_drawn, read_sheets


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


_FILED_SHEET = [
    # Schedule A/B's fifth and sixth vehicles, on its attached sheet, under the filer's name.
    ("Maria Torres", (("3.5", "Volvo", "500.00"), ("3.6", "Kia", "600.00")))
]


@pytest.mark.parametrize(
    "form_type, parts, box, printed, sheets",
    [
        ("form_121", ["form"], "Debtor1.First name", {(None, "Maria")}, []),
        # Schedule D's sixth row prints on a copy of page 2, under the filer's name.
        (
            "schedule_d",
            ["form", "copy"],
            "Debtor 1",
            {(None, "Maria Torres"), (1, "Maria Torres")},
            [],
        ),
        ("schedule_a_b", ["form", "sheet"], "Debtor 1", {(None, "Maria Torres")}, _FILED_SHEET),
    ],
    ids=["form", "with a copy", "with a sheet"],
)
def test_a_filed_form_downloads_exactly_what_was_filed(
    api_client_authed,
    generated_form_factory,
    schedule_d_with_copies,
    schedule_a_b_with_sheet,
    creditor_payments,
    form_type,
    parts,
    box,
    printed,
    sheets,
):
    form = generated_form_factory(status="generated")
    form.form_type = form_type
    form.save()
    rows = creditor_payments(
        form.session, 6, ["Honda", "Toyota", "Subaru", "Mazda", "Volvo", "Kia"]
    )
    regenerate = reverse("generated-forms-regenerate", kwargs={"pk": form.pk})
    mark_filed = reverse("generated-forms-mark-filed", kwargs={"pk": form.pk})
    assert api_client_authed.post(regenerate).status_code == 200
    assert api_client_authed.post(mark_filed).status_code == 200
    form.refresh_from_db()
    filed = form.field_values
    # Spec §6's parts document: a version, the form's own part, then one part per copy, then
    # one per attached sheet.
    document = json.loads(filed)
    assert (document["version"], [part["kind"] for part in document["parts"]]) == (2, parts)
    _rename_filer(form, "Marisol")  # the filer's later edits
    rows[5].delete()  # Schedule D would now print five rows, and no copy; A/B one sheet row

    response = _download(api_client_authed, form)

    assert response.status_code == 200
    drawn = read_drawn(form_type, response.content, document["parts"])
    assert {(w.copy, w.value) for w in drawn if w.full_name == box} == printed
    spec = load_schema("schedule_a_b").groups["ab_line_3"].sheet
    assert [(page.header[0], page.rows) for page in read_sheets(response.content, spec)] == sheets
    form.refresh_from_db()
    assert (form.status, form.field_values) == ("filed", filed)


def _words(pdf):
    """Each page's words with their boxes, as MuPDF reads them."""
    return [page.get_text("words") for page in pymupdf.open("pdf", pdf)]


def _ab_group(change):
    """Change the synthetic Schedule A/B group's declaration."""
    return lambda d: change(d["groups"]["ab_line_3"])


def _rename_the_group(d):
    d["groups"]["ab_vehicles"] = d["groups"].pop("ab_line_3")
    for f in d["fields"]:
        if f["repeat"] == "ab_line_3":
            f["repeat"] = "ab_vehicles"


def _add_a_column(d):
    columns = d["groups"]["ab_line_3"]["sheet"]["columns"]
    columns[0]["width"] = 200
    columns.insert(
        1, {"label": "Model", "binding": "sofa.creditor_payments[].creditor_name", "width": 100}
    )


def _relabel(sheet):
    sheet["title"] = "Schedule A/B (renamed)"
    sheet["columns"][0]["label"] = "Model"


@pytest.mark.parametrize(
    "edit",
    [
        _rename_the_group,
        _add_a_column,
        _ab_group(lambda g: g["sheet"]["columns"][0].update(width=29)),
        _ab_group(lambda g: _relabel(g["sheet"])),
    ],
    ids=["rename the group", "add a column", "narrow a column", "relabel"],
)
def test_a_filed_sheet_prints_what_was_filed_whatever_its_schema_says_later(
    api_client_authed, generated_form_factory, schedule_a_b_with_sheet, creditor_payments, edit
):
    # A sheet part stores the title and columns it was drawn with (R63), so a schema edit
    # that passes startup changes nothing a filed form prints (spec §6, DIG-155).
    form = generated_form_factory(status="generated")
    form.form_type = "schedule_a_b"
    form.save()
    creditor_payments(form.session, 6, ["Honda", "Toyota", "Subaru", "Mazda", "Volvo", "Kia"])
    regenerate = reverse("generated-forms-regenerate", kwargs={"pk": form.pk})
    mark_filed = reverse("generated-forms-mark-filed", kwargs={"pk": form.pk})
    assert api_client_authed.post(regenerate).status_code == 200
    assert api_client_authed.post(mark_filed).status_code == 200
    filed = _download(api_client_authed, form)
    path = schedule_a_b_with_sheet / "schedule_a_b.json"
    schema = json.loads(path.read_text())
    edit(schema)
    path.write_text(json.dumps(schema))
    load_schema.cache_clear()
    assert validate_form("schedule_a_b") == []

    response = _download(api_client_authed, form)

    assert response.status_code == 200
    # Every word of every page, where it prints. (The bytes differ: each PDF has its own /ID.)
    assert _words(response.content) == _words(filed.content)


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


def test_rows_past_the_slots_download_on_a_copy(
    api_client_authed, generated_form_factory, schedule_d_with_copies, creditor_payments
):
    form = generated_form_factory(status="generated")
    form.form_type = "schedule_d"
    form.save()
    rows = creditor_payments(form.session, 6)

    response = _download(api_client_authed, form)

    assert response.status_code == 200
    form.refresh_from_db()
    parts = json.loads(form.field_values)["parts"]
    assert [part["kind"] for part in parts] == ["form", "copy"]
    # Page 2's first slot holds the third row; its copy holds the sixth.
    drawn = read_drawn("schedule_d", response.content, parts)
    assert {(w.copy, w.value) for w in drawn if w.full_name == "Creditors Name_3"} == {
        (None, rows[2].creditor_name),
        (1, rows[5].creditor_name),
    }


@pytest.mark.parametrize(
    "count, entries",
    [
        (6, ["2.3", "2.4", "2.5", "2.6", "", ""]),
        (8, ["2.3", "2.4", "2.5", "2.6", "2.7", "2.8"]),
    ],
    ids=["one row on the copy", "a full copy"],
)
def test_a_page_of_guarded_slots_still_takes_its_rows_on_a_copy(
    api_client_authed,
    generated_form_factory,
    schedule_d_with_copies,
    creditor_payments,
    count,
    entries,
):
    # UPL guard: page 2's boxes print only an asked answer, so they print nothing here. The
    # guard decides which boxes print, never which slots exist: rows past the last slot
    # still go to the copy's slots, numbered, as rows 3 to 5 do on page 2.
    path = schedule_d_with_copies / "schedule_d.json"
    data = json.loads(path.read_text())
    for f in data["fields"]:
        if f["repeat"] == "d_part_1" and f["page"] == 2:
            f.update(source="derived", rule="full_name", legal_review=True)
    path.write_text(json.dumps(data))
    load_schema.cache_clear()
    form = generated_form_factory(status="generated")
    form.form_type = "schedule_d"
    form.save()
    rows = creditor_payments(form.session, count)

    response = _download(api_client_authed, form)

    assert response.status_code == 200
    form.refresh_from_db()
    parts = json.loads(form.field_values)["parts"]
    drawn = read_drawn("schedule_d", response.content, parts)
    assert [w.value for w in drawn if w.full_name in ("undefined_12", "undefined_19")] == entries
    text = "".join(page.get_text() for page in pymupdf.open("pdf", response.content))
    assert rows[0].creditor_name in text  # page 1's boxes aren't guarded
    guarded = {r.creditor_name for r in rows[2:]} | {str(r.total_paid) for r in rows[2:]}
    assert [value for value in guarded if value in text] == []


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
