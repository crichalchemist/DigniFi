"""Unit tests for GeminiProvider."""

import os
from unittest.mock import MagicMock, patch

import pytest

from apps.documents.services.providers.gemini import GeminiProvider


@pytest.fixture
def mock_genai_client():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.gemini.genai") as mock_genai:
            mock_response = MagicMock()
            mock_response.text = '{"document_type": "pay_stub"}'
            mock_genai.Client.return_value.models.generate_content.return_value = mock_response
            yield mock_genai.Client.return_value


@pytest.fixture
def provider(mock_genai_client):
    return GeminiProvider()


class TestGeminiProviderClassify:
    def test_text_mode_when_no_image(self, provider, mock_genai_client):
        result = provider.classify(b"", "Is this a pay stub?")
        call_args = mock_genai_client.models.generate_content.call_args
        assert call_args.kwargs["contents"] == "Is this a pay stub?"
        assert call_args.kwargs.get("config") is None
        assert result == '{"document_type": "pay_stub"}'

    def test_vision_mode_when_image_provided(self, provider, mock_genai_client):
        provider.classify(b"\xff\xd8\xff", "Classify this document")
        call_args = mock_genai_client.models.generate_content.call_args
        contents = call_args.kwargs["contents"]
        assert isinstance(contents, list)
        assert len(contents) == 2

    def test_no_json_mime_type_on_classify(self, provider, mock_genai_client):
        provider.classify(b"", "Classify")
        call_args = mock_genai_client.models.generate_content.call_args
        assert call_args.kwargs.get("config") is None


class TestGeminiProviderExtract:
    def test_text_mode_sets_json_mime(self, provider, mock_genai_client):

        provider.extract(b"", "Extract fields")
        call_args = mock_genai_client.models.generate_content.call_args
        config = call_args.kwargs.get("config")
        assert config is not None
        assert config.response_mime_type == "application/json"

    def test_vision_mode_sets_json_mime(self, provider, mock_genai_client):

        provider.extract(b"\xff\xd8\xff", "Extract fields from image")
        call_args = mock_genai_client.models.generate_content.call_args
        config = call_args.kwargs.get("config")
        assert config is not None
        assert config.response_mime_type == "application/json"

    def test_returns_empty_string_on_none_response(self, mock_genai_client):
        mock_genai_client.models.generate_content.return_value.text = None
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("apps.documents.services.providers.gemini.genai") as mock_g:
                mock_g.Client.return_value = mock_genai_client
                p = GeminiProvider()
        result = p.extract(b"", "Extract")
        assert result == ""

    def test_vision_mode_passes_image_part_first(self, provider, mock_genai_client):
        provider.extract(b"\xff\xd8\xff", "Extract")
        call_args = mock_genai_client.models.generate_content.call_args
        contents = call_args.kwargs["contents"]
        assert isinstance(contents, list)
        # first element is the image Part, second is the prompt string
        assert isinstance(contents[1], str)
