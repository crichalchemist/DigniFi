"""Unit tests for OpenAIProvider."""

import os
from unittest.mock import MagicMock, patch

import pytest

from apps.documents.services.providers.base import EmptyModelReply
from apps.documents.services.providers.openai_provider import OpenAIProvider
from apps.documents.tests.builders import chat_completion


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

    @pytest.mark.parametrize(
        "pages",
        [
            [b"\xff\xd8\xff"],
            [b"\xff\xd8\xff\x00binary"],
            [b"page-1", b"page-2", b"page-3"],
        ],
        ids=["one_page", "binary_page", "three_pages"],
    )
    def test_every_scanned_page_is_sent_in_page_order(self, provider, mock_openai_client, pages):
        import base64

        provider.extract(pages, "Return ONLY a valid JSON object.")
        content = _sent_content(mock_openai_client)
        assert [part["type"] for part in content] == ["image_url"] * len(pages) + ["text"]
        prefix = "data:image/jpeg;base64,"
        urls = [part["image_url"]["url"] for part in content[: len(pages)]]
        assert all(url.startswith(prefix) for url in urls)
        assert [base64.b64decode(url.removeprefix(prefix)) for url in urls] == pages


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


class TestEmptyReplies:
    """An empty reply used to reach json.loads and fail as unparseable, leaving no trace
    of why. It is now retried once when a retry can help, and the error says why the
    reply was empty without quoting anything the model wrote."""

    def test_a_whitespace_reply_is_retried_once_then_reported(self, provider, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = chat_completion(
            " \n\t", finish_reason="length"
        )
        with pytest.raises(EmptyModelReply, match=r"finish_reason=length, refusal=absent"):
            provider.extract([], "Return ONLY a valid JSON object.")
        assert mock_openai_client.chat.completions.create.call_count == 2

    def test_a_retry_that_answers_is_used(self, provider, mock_openai_client):
        mock_openai_client.chat.completions.create.side_effect = [
            chat_completion(None),
            chat_completion('{"creditor_name": "Lakeshore Medical Billing"}'),
        ]
        reply = provider.extract([], "Return ONLY a valid JSON object.")
        assert reply == '{"creditor_name": "Lakeshore Medical Billing"}'

    def test_a_refusal_is_not_retried_and_its_wording_is_not_kept(
        self, provider, mock_openai_client
    ):
        mock_openai_client.chat.completions.create.return_value = chat_completion(
            None, refusal="I can't read the statement for Jordan Sample, SSN 900-12-3456."
        )
        with pytest.raises(EmptyModelReply) as raised:
            provider.extract([b"\xff\xd8\xff"], "Return ONLY a valid JSON object.")
        assert mock_openai_client.chat.completions.create.call_count == 1
        assert "refusal=present" in str(raised.value)
        assert "Jordan Sample" not in str(raised.value)
        assert "900-12-3456" not in str(raised.value)

    def test_a_filtered_reply_is_not_retried(self, provider, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = chat_completion(
            None, finish_reason="content_filter"
        )
        with pytest.raises(EmptyModelReply, match="finish_reason=content_filter"):
            provider.extract([b"\xff\xd8\xff"], "Return ONLY a valid JSON object.")
        assert mock_openai_client.chat.completions.create.call_count == 1
