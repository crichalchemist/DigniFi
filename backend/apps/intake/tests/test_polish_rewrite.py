"""
The one send to the AI service for a line 43 rewrite (3h4 spec 5, 6.3, 7.1): the client is built and
called with every argument pinned, only the filer's text goes out, one press is one send, every
reply is checked and refused with one word, and every failure leaves no filer text or model text in
the exception. Synthetic text only. The SDK's client class is the boundary that is replaced.

No database: polish_builders.polish_sdk() turns the polish on with override_settings as a context
manager, which needs none.
"""

from unittest.mock import patch

import httpx2
import pytest
from anthropic import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)
from anthropic.types import ThinkingBlock
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.forms.tests.means_rows import POLISH_DEMO_EXPLANATION
from apps.intake import polish
from apps.intake.polish import (
    BASE_URL,
    DEFAULT_MODEL,
    REASONS,
    SYSTEM_PROMPT,
    NoRewrite,
    PolishUnavailable,
)
from apps.intake.tests import polish_builders
from apps.intake.tests.polish_builders import empty_message, message, refusal_message

ORIGINAL = "I pay 1,400 each month for my treatment."


@pytest.fixture
def polish_sdk():
    with polish_builders.polish_sdk() as client_cls:
        yield client_cls


def _create(client_cls, reply=None, error=None):
    create = client_cls.return_value.messages.create
    create.return_value = reply
    create.side_effect = error
    return create


def test_the_client_is_built_with_every_argument_explicit(polish_sdk):
    """The SDK reads a key, a base URL and a ten-minute timeout from the shell and retries on its
    own unless each is given, so every argument is given."""
    _create(polish_sdk, message("Demo rewrite."))

    polish.rewrite("My job ended.")

    assert polish_sdk.call_args.kwargs == {
        "api_key": "test-key",
        "base_url": BASE_URL,
        "timeout": 30.0,
        "max_retries": 0,
    }
    assert set(polish_sdk.call_args.kwargs) == {"api_key", "base_url", "timeout", "max_retries"}
    assert not polish_sdk.call_args.args


def test_the_shells_base_url_is_ignored(polish_sdk, monkeypatch):
    """A shell that points the SDK at another host must not redirect a filer's words."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:4011")
    _create(polish_sdk, message("Demo rewrite."))

    polish.rewrite("My job ended.")

    assert polish_sdk.call_args.kwargs["base_url"] == BASE_URL == "https://api.anthropic.com"


def test_the_request_carries_exactly_five_arguments_and_the_text_alone(polish_sdk):
    """Nothing but the model, the cap, the fixed instructions, the filer's trimmed-by-the-caller
    words and the effort leaves the server: no metadata, no user id, no extra field."""
    create = _create(polish_sdk, message("Demo rewrite."))
    text = "My job ended."

    polish.rewrite(text)

    assert create.call_count == 1
    assert set(create.call_args.kwargs) == {
        "model",
        "max_tokens",
        "system",
        "messages",
        "output_config",
    }
    assert create.call_args.kwargs["messages"] == [{"role": "user", "content": text}]
    assert create.call_args.kwargs["system"] == SYSTEM_PROMPT
    assert create.call_args.kwargs["max_tokens"] == 4000
    assert create.call_args.kwargs["output_config"] == {"effort": "low"}
    assert create.call_args.kwargs["model"] == DEFAULT_MODEL == "claude-sonnet-5-5"
    with override_settings(AI_POLISH_MODEL="demo-model"):
        polish.rewrite(text)
    assert create.call_args.kwargs["model"] == "demo-model"


ORIGINAL_LESS_ITS_FIGURE = ORIGINAL.replace("1,400 ", "")

REFUSED = [
    pytest.param(empty_message(), ORIGINAL, "empty", id="no text block"),
    pytest.param(message("  \n "), ORIGINAL, "empty", id="whitespace only"),
    pytest.param(refusal_message(), ORIGINAL, "refusal", id="safety refusal"),
    pytest.param(
        message("Demo rewrite.", stop_reason="max_tokens"), ORIGINAL, "max_tokens", id="cut off"
    ),
    pytest.param(message("a" * 2001), ORIGINAL, "too_long", id="2001 characters"),
    pytest.param(message("\n".join(["Demo line."] * 37)), ORIGINAL, "unprintable", id="37 lines"),
    pytest.param(message("My job ended □."), ORIGINAL, "unprintable", id="a square"),
    pytest.param(message("I recommend you file."), ORIGINAL, "phrase", id="a phrase"),
    pytest.param(
        message(ORIGINAL + " Demo Clinic 7,777"), ORIGINAL, "added_facts", id="a figure and a name"
    ),
    pytest.param(
        message(ORIGINAL_LESS_ITS_FIGURE), ORIGINAL, "dropped_facts", id="a figure dropped"
    ),
    pytest.param(
        message("I'm sorry, but I can't rewrite this."),
        POLISH_DEMO_EXPLANATION,
        "dropped_facts",
        id="refusal prose, its six facts gone before the floor",
    ),
    pytest.param(
        message("Since March 2025 I pay 1,400 monthly to Demo Clinic for my illness care."),
        POLISH_DEMO_EXPLANATION,
        "too_short",
        id="every fact kept in under half the words",
    ),
    pytest.param(
        message("Since March 2025 I pay monthly to Demo Clinic for my illness care."),
        POLISH_DEMO_EXPLANATION,
        "dropped_facts",
        id="short and a figure dropped: the first failing check names it",
    ),
]


@pytest.mark.parametrize(("reply", "original", "reason"), REFUSED)
def test_each_refused_reply_names_one_reason_and_is_sent_once(polish_sdk, reply, original, reason):
    """A reply the filer must not see is refused with one word, and the filer's words are not sent
    again to try for a better one."""
    create = _create(polish_sdk, reply)

    with pytest.raises(NoRewrite) as raised:
        polish.rewrite(original)

    assert str(raised.value) == reason
    assert str(raised.value) in REASONS
    assert create.call_count == 1


def test_a_reply_with_a_thinking_block_is_read_from_its_text_blocks(polish_sdk):
    """Sonnet 5.5 thinks by default: a real reply carries a thinking block, with no text, before
    its text block. Reading every block's text would fail every real press."""
    reply = message("Demo rewrite.")
    reply.content = [ThinkingBlock(type="thinking", thinking="", signature="demo"), *reply.content]
    _create(polish_sdk, reply)

    assert polish.rewrite("My job ended.") == "Demo rewrite."


@pytest.mark.parametrize(
    ("original", "reply", "returned"),
    [
        pytest.param("My job ended.", "  Demo rewrite. \n", "Demo rewrite.", id="stripped"),
        pytest.param(
            ORIGINAL,
            "I pay 1400 each month for my treatment.",
            "I pay 1400 each month for my treatment.",
            id="1,400 as 1400",
        ),
        pytest.param(
            "I am worried about my rent and my bills.",
            "I'm worried about my rent and my bills.",
            "I'm worried about my rent and my bills.",
            id="I am as I'm",
        ),
        pytest.param(
            "My rent goes up each month and I cannot pay it.",
            "My rent may go up each month and I cannot pay it.",
            "My rent may go up each month and I cannot pay it.",
            id="a modal added",
        ),
    ],
)
def test_a_rewrite_that_keeps_the_filers_facts_is_returned_stripped(
    polish_sdk, original, reply, returned
):
    """Wording may change; the filer's facts may not, and the text returned is what the model
    wrote, without the whitespace around it."""
    _create(polish_sdk, message(reply))

    assert polish.rewrite(original) == returned


def _request(**headers):
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages", headers=headers)


def _status_error(cls, status):
    request = _request()
    response = httpx2.Response(status, request=request)
    return cls("req_demo_123 Demo Clinic 7,777", response=response, body=None)


SDK_ERRORS = [
    APITimeoutError(_request(**{"request-id": "req_demo_123"})),
    APIConnectionError(message="Connection error.", request=_request(**{"x-id": "req_demo_123"})),
    _status_error(RateLimitError, 429),
    _status_error(InternalServerError, 500),
    _status_error(AuthenticationError, 401),
]


@pytest.mark.parametrize("error", SDK_ERRORS, ids=lambda error: type(error).__name__)
def test_every_sdk_error_is_one_class_name_and_nothing_else(polish_sdk, error):
    """An SDK error can carry a request id or text from the vendor's body; none of it may reach a
    log, so the one error the view sees is the SDK's class name."""
    _create(polish_sdk, error=error)

    with pytest.raises(PolishUnavailable) as raised:
        polish.rewrite("My job ended.")

    assert str(raised.value) == type(error).__name__
    assert "req_demo_123" not in str(raised.value)


def test_an_error_that_is_not_the_sdks_is_not_swallowed(polish_sdk):
    """Only the SDK's errors mean the service is unreachable. A bug of ours must come out as
    itself, not wear the same one-word mask and read as an outage."""
    _create(polish_sdk, error=TypeError("demo"))

    with pytest.raises(TypeError):
        polish.rewrite("My job ended.")


@pytest.mark.parametrize(
    ("provider", "key", "variable", "configured"),
    [
        ("gemini", "k", "AI_POLISH_PROVIDER", False),
        ("sk-demo-key", "k", "AI_POLISH_PROVIDER", False),
        ("anthropic", "", "AI_POLISH_API_KEY", False),
        ("", "", "AI_POLISH_PROVIDER", False),
        ("anthropic", "k", None, True),
        ("ANTHROPIC", "k", None, True),
    ],
)
def test_an_unknown_or_empty_provider_and_an_empty_key_raise_at_use_by_variable_name(
    settings, provider, key, variable, configured
):
    """A misset variable fails the press, never the boot, and names the variable and never its
    value: a key pasted into the provider variable must not reach a log."""
    settings.AI_POLISH_PROVIDER = provider
    settings.AI_POLISH_API_KEY = key
    assert polish.configured() is configured
    if configured:
        return

    with patch("anthropic.Anthropic") as client_cls, pytest.raises(ImproperlyConfigured) as raised:
        polish.rewrite("My job ended.")

    assert variable in str(raised.value)
    assert "gemini" not in str(raised.value)
    assert "sk-demo" not in str(raised.value)
    client_cls.assert_not_called()
