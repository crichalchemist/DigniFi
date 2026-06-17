"""
Tests for the GET /api/forms/{id}/download/ endpoint.

Covers:
  - GET returns application/pdf with correct content
  - download transitions status generated -> downloaded
  - 501 returned when generator lacks pdf_field_map()
"""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_download_returns_pdf(api_client_authed, generated_form_factory):
    """GET /api/forms/{id}/download/ streams application/pdf."""
    form = generated_form_factory(status="generated")
    fake_pdf = b"%PDF-1.4 fake content"

    with (
        patch("apps.forms.views.get_generator") as mock_gen_cls,
        patch("apps.forms.views.PDFFormFiller") as mock_filler_cls,
    ):
        mock_gen = MagicMock()
        mock_gen.pdf_field_map.return_value = {"Debtor1.First name": "Maria"}
        mock_gen_cls.return_value = mock_gen

        mock_filler = MagicMock()
        mock_filler.fill.return_value = fake_pdf
        mock_filler_cls.return_value = mock_filler

        url = reverse("generated-forms-download", kwargs={"pk": form.pk})
        response = api_client_authed.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert b"%PDF" in response.content


@pytest.mark.django_db
def test_download_marks_form_downloaded(api_client_authed, generated_form_factory):
    """download action transitions status generated -> downloaded."""
    form = generated_form_factory(status="generated")
    fake_pdf = b"%PDF-1.4 fake"

    with (
        patch("apps.forms.views.get_generator") as mock_gen_cls,
        patch("apps.forms.views.PDFFormFiller") as mock_filler_cls,
    ):
        mock_gen_cls.return_value.pdf_field_map.return_value = {}
        mock_filler_cls.return_value.fill.return_value = fake_pdf
        url = reverse("generated-forms-download", kwargs={"pk": form.pk})
        api_client_authed.get(url)

    form.refresh_from_db()
    assert form.status == "downloaded"


@pytest.mark.django_db
def test_download_returns_422_on_repeat_overflow(api_client_authed, generated_form_factory):
    """download returns 422 when resolver hits RepeatOverflow."""
    from apps.forms.services.fill_resolver import RepeatOverflow

    form = generated_form_factory(status="generated")
    with patch("apps.forms.views.get_generator") as mock_gen_cls:
        mock_gen_cls.return_value.pdf_field_map.side_effect = RepeatOverflow("form_107", "cp", 3, 5)
        url = reverse("generated-forms-download", kwargs={"pk": form.pk})
        response = api_client_authed.get(url)

    assert response.status_code == 422
    assert "continuation" in response.json()["detail"].lower()


@pytest.mark.django_db
def test_download_returns_500_on_missing_template(api_client_authed, generated_form_factory):
    """download returns 500 when PDF template file is missing."""
    form = generated_form_factory(status="generated")
    with (
        patch("apps.forms.views.get_generator") as mock_gen_cls,
        patch("apps.forms.views.PDFFormFiller") as mock_filler_cls,
    ):
        mock_gen_cls.return_value.pdf_field_map.return_value = {"F": "v"}
        mock_filler_cls.return_value.fill.side_effect = FileNotFoundError("b_107_0425-form.pdf")
        url = reverse("generated-forms-download", kwargs={"pk": form.pk})
        response = api_client_authed.get(url)

    assert response.status_code == 500
    assert "detail" in response.json()


@pytest.mark.django_db
def test_download_returns_501_when_mapping_not_implemented(
    api_client_authed, generated_form_factory
):
    """download returns 501 when generator lacks pdf_field_map()."""
    form = generated_form_factory(status="generated")

    with patch("apps.forms.views.get_generator") as mock_gen_cls:
        mock_gen_cls.return_value.pdf_field_map.side_effect = NotImplementedError
        url = reverse("generated-forms-download", kwargs={"pk": form.pk})
        response = api_client_authed.get(url)

    assert response.status_code == 501
