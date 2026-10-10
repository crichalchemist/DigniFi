"""Unit tests for OpenAIProvider."""

import os
from unittest.mock import MagicMock, patch

import pytest

from apps.documents.services.providers.openai_provider import OpenAIProvider


@pytest.fixture
def mock_openai_client():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.openai_provider.OpenAI") as mock_openai:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = '{"document_type": "pay_stub"}'
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            yield mock_openai.return_value


@pytest.fixture
def provider(mock_openai_client):
    return OpenAIProvider()


def _sent_content(client) -> list:
    """The user message content of the single completion call."""
    kwargs = client.chat.completions.create.call_args.kwargs
    return kwargs["messages"][0]["content"]


class TestTextVersusVisionRouting:
    """Text-extracted PDFs must not be re-sent as images, and scanned pages must not
    be silently dropped — either mistake loses the debtor's document contents."""

    def test_markdown_only_document_is_sent_as_text(self, provider, mock_openai_client):
        provider.extract([], "Return ONLY a valid JSON object for this pay stub.")
        content = _sent_content(mock_openai_client)
        assert [part["type"] for part in content] == ["text"]

    def test_scanned_page_is_sent_as_an_inline_image(self, provider, mock_openai_client):
        provider.extract([b"\xff\xd8\xff"], "Return ONLY a valid JSON object.")
        content = _sent_content(mock_openai_client)
        assert [part["type"] for part in content] == ["image_url", "text"]
        assert content[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")

    def test_image_bytes_survive_the_round_trip_intact(self, provider, mock_openai_client):
        import base64

        provider.extract([b"\xff\xd8\xff\x00binary"], "Return ONLY a valid JSON object.")
        url = _sent_content(mock_openai_client)[0]["image_url"]["url"]
        encoded = url.removeprefix("data:image/jpeg;base64,")
        assert base64.b64decode(encoded) == b"\xff\xd8\xff\x00binary"

    def test_every_scanned_page_is_sent_in_page_order(self, provider, mock_openai_client):
        import base64

        provider.extract([b"page-1", b"page-2", b"page-3"], "Return ONLY a valid JSON object.")
        content = _sent_content(mock_openai_client)
        assert [part["type"] for part in content] == ["image_url", "image_url", "image_url", "text"]
        sent = [
            base64.b64decode(part["image_url"]["url"].removeprefix("data:image/jpeg;base64,"))
            for part in content[:3]
        ]
        assert sent == [b"page-1", b"page-2", b"page-3"]


class TestStructuredOutputGuarantee:
    """DocumentProcessor._parse_result runs json.loads on whatever comes back. Extraction
    must therefore constrain the response to JSON; classification is free-text by design."""

    def test_extraction_constrains_the_response_to_json(self, provider, mock_openai_client):
        provider.extract([], "Return ONLY a valid JSON object.")
        kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}

    def test_classification_does_not_constrain_the_response(self, provider, mock_openai_client):
        provider.classify(b"", "Is this a pay stub?")
        kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert "response_format" not in kwargs


class TestProviderContract:
    """BaseOCRProvider promises a str. A None completion must not leak downstream as a
    TypeError inside json.loads."""

    def test_empty_completion_becomes_empty_string(self, provider, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = None
        assert provider.extract([], "Return ONLY a valid JSON object.") == ""

    def test_configured_model_is_the_one_requested(self, mock_openai_client):
        OpenAIProvider(model="gpt-4o-mini").extract([], "Return ONLY a valid JSON object.")
        kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "gpt-4o-mini"
