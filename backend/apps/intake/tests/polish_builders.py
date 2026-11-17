"""Builders for the line 43 AI polish tests: a reply the SDK would return, and the one stand-in
for the SDK's client. Synthetic text only."""

from contextlib import contextmanager
from unittest.mock import patch

from anthropic.types import Message, TextBlock, Usage
from django.test import override_settings


def message(text, *, stop_reason="end_turn"):
    """A reply with one text block, built from the SDK's own Message so a field the SDK renames
    breaks the test, not production."""
    return Message(
        id="msg_demo",
        content=[TextBlock(type="text", text=text)],
        model="claude-sonnet-5-5",
        role="assistant",
        type="message",
        usage=Usage(input_tokens=1, output_tokens=1),
        stop_reason=stop_reason,
    )


def empty_message():
    """A reply that ended normally with no text block at all."""
    reply = message("")
    reply.content = []
    return reply


def refusal_message():
    """A safety refusal: HTTP 200 with stop_reason "refusal" and no text."""
    reply = empty_message()
    reply.stop_reason = "refusal"
    return reply


@contextmanager
def polish_sdk():
    """The polish turned on with a key, and the SDK's client class replaced: yields the patched
    class. rewrite imports the SDK inside the function, so the class is patched where it lives."""
    with (
        override_settings(AI_POLISH_PROVIDER="anthropic", AI_POLISH_API_KEY="test-key"),
        patch("anthropic.Anthropic") as client_cls,
    ):
        yield client_cls
