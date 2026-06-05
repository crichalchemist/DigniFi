"""Tests for LlamaCppProvider."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from apps.documents.services.providers.base import BaseOCRProvider
from apps.documents.services.providers.llama_cpp import LlamaCppProvider


@pytest.fixture
def provider():
    """Fixture providing LlamaCppProvider with mocked OpenAI client."""
    with patch("apps.documents.services.providers.llama_cpp.OpenAI"):
        return LlamaCppProvider(base_url="http://llm:8080/v1")


def test_provider_implements_base_interface(provider):
    """LlamaCppProvider should implement BaseOCRProvider interface."""
    assert isinstance(provider, BaseOCRProvider)


def test_classify_calls_vision_api(provider):
    """classify() should call vision API with image data."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "pay_stub"
    provider.client.chat.completions.create.return_value = mock_response

    image_data = b"\x89PNG\r\n\x1a\n"
    result = provider.classify(image_data, "What document type is this?")

    provider.client.chat.completions.create.assert_called_once()
    assert result == "pay_stub"


def test_extract_with_image_calls_vision_api(provider):
    """extract() with image data should call vision API."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"amount_owed": "500"}'
    provider.client.chat.completions.create.return_value = mock_response

    image_data = b"\x89PNG\r\n"
    result = provider.extract(image_data, "Extract fields from this document")

    provider.client.chat.completions.create.assert_called_once()
    assert "amount_owed" in result


def test_extract_without_image_calls_text_api(provider):
    """extract() without image data should call text API."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"creditor": "Bank"}'
    provider.client.chat.completions.create.return_value = mock_response

    result = provider.extract(b"", "Extract creditor name from text")

    provider.client.chat.completions.create.assert_called_once()
    assert "creditor" in result


def test_vision_api_encodes_image_as_base64(provider):
    """_call_vision should base64 encode image data."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "success"
    provider.client.chat.completions.create.return_value = mock_response

    image_data = b"fake_png_data"
    provider.classify(image_data, "Classify this")

    # Get the call arguments
    call_args = provider.client.chat.completions.create.call_args
    kwargs = call_args.kwargs
    messages = kwargs["messages"]

    # Verify base64 encoding in image_url
    image_url = messages[0]["content"][1]["image_url"]["url"]
    assert "data:image/jpeg;base64," in image_url
    expected_b64 = base64.b64encode(image_data).decode("utf-8")
    assert expected_b64 in image_url


def test_api_call_uses_gemma_model(provider):
    """API calls should use gemma-3-4b-it model."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "result"
    provider.client.chat.completions.create.return_value = mock_response

    provider.classify(b"image_data", "Classify")

    call_args = provider.client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "gemma-3-4b-it"


def test_api_call_temperature_is_low(provider):
    """API calls should use temperature 0.1 for deterministic output."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "result"
    provider.client.chat.completions.create.return_value = mock_response

    provider.extract(b"", "Extract data")

    call_args = provider.client.chat.completions.create.call_args
    assert call_args.kwargs["temperature"] == 0.1


def test_api_call_max_tokens_limit(provider):
    """API calls should limit max_tokens to 1024."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "result"
    provider.client.chat.completions.create.return_value = mock_response

    provider.classify(b"image_data", "Classify")

    call_args = provider.client.chat.completions.create.call_args
    assert call_args.kwargs["max_tokens"] == 1024


def test_client_initialized_with_correct_base_url():
    """OpenAI client should be initialized with correct base_url."""
    with patch("apps.documents.services.providers.llama_cpp.OpenAI") as mock_openai:
        LlamaCppProvider(base_url="http://llm:8080/v1")

        # Verify OpenAI was called with correct base_url
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["base_url"] == "http://llm:8080/v1"


def test_client_no_api_key_required():
    """OpenAI client should not require real API key for local deployment."""
    with patch("apps.documents.services.providers.llama_cpp.OpenAI") as mock_openai:
        LlamaCppProvider(base_url="http://localhost:8080/v1")

        # Verify OpenAI was called with api_key='not-required'
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["api_key"] == "not-required"
        assert call_kwargs["base_url"] == "http://localhost:8080/v1"


def test_client_accepts_custom_api_key():
    """Custom api_key should be forwarded to OpenAI client (Heroku Managed Inference path)."""
    with patch("apps.documents.services.providers.llama_cpp.OpenAI") as mock_openai:
        LlamaCppProvider(
            base_url="https://inference.heroku.com/v1",
            api_key="sk-heroku-test-key",
        )

        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["api_key"] == "sk-heroku-test-key"
        assert call_kwargs["base_url"] == "https://inference.heroku.com/v1"


def test_api_calls_use_configured_model():
    """Model name passed to constructor should be used in every API call."""
    with patch("apps.documents.services.providers.llama_cpp.OpenAI"):
        provider = LlamaCppProvider(model="claude-sonnet-4-5")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "result"
    provider.client.chat.completions.create.return_value = mock_response

    provider.classify(b"image_data", "Classify")

    call_args = provider.client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "claude-sonnet-4-5"
