# ruff: noqa: F811
"""The line 43 AI polish: a filer's words go to a hosted service only by deliberate setup, only
the explanation goes, and what comes back is checked before the filer sees it.

The first two tests are the settings that gate it; the rest are the endpoint's.
"""

import importlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import environ
import httpx2
import pytest
from anthropic import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from anthropic.types import TextBlock
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.forms.models import model_to_dict
from django.test import override_settings
from rest_framework.test import APIClient

import config.settings.base as base_settings
from apps.audit.models import AuditLog
from apps.forms.tests.means_rows import POLISH_DEMO_EXPLANATION
from apps.forms.tests.test_means_hold import (  # noqa: F401, F811
    above,
    district,
    session_with_debtor,
    user,
)
from apps.intake import polish
from apps.intake.means_test import (
    MEANS_EXPLANATION_TOO_LONG,
    MEANS_POLISH_BLANK,
    MEANS_POLISH_IDENTIFIER,
    MEANS_POLISH_NO_REWRITE,
    MEANS_POLISH_PHRASE,
    MEANS_POLISH_UNAVAILABLE,
    NOT_A_MEANS_ANSWER,
)
from apps.intake.models import IntakeSession, MeansTestAnswers, SecuredDebtAnswers
from apps.intake.polish import BASE_URL, SYSTEM_PROMPT, PolishThrottle
from apps.intake.polish_checks import LEGAL_CONCLUSIONS, POLISH_PHRASES
from apps.intake.tests import polish_builders
from apps.intake.tests.builders import answer_means_test, complete_debt
from apps.intake.tests.polish_builders import empty_message, message, refusal_message

User = get_user_model()

SENT = (
    "Demo explanation: my hours were cut in March 2025 and Demo Clinic billed 1,400 for the stay."
)
REWRITE = "Demo rewrite: my hours were cut in March 2025 and Demo Clinic billed 1,400 for the stay."
# An original that names no clinic, so a rewrite that adds one adds a name.
NO_CLINIC = "My hours were cut in March 2025 and the lab billed 1,400 for the stay."
NO_REWRITE = {"error": MEANS_POLISH_NO_REWRITE}
UNAVAILABLE = {"error": MEANS_POLISH_UNAVAILABLE}


def test_a_deploy_that_names_no_polish_provider_ships_empty_defaults(monkeypatch):
    """A deploy that sets no AI_POLISH_* variable must leave the polish off, so no filer's
    words reach a vendor until someone chooses one on purpose."""
    for name in ("AI_POLISH_PROVIDER", "AI_POLISH_API_KEY", "AI_POLISH_MODEL"):
        monkeypatch.delenv(name, raising=False)
    # A developer's repo-root .env must not stand in for the shipped default.
    monkeypatch.setattr(environ.Env, "read_env", lambda *args, **kwargs: None)
    try:
        reloaded = importlib.reload(base_settings)
        assert reloaded.AI_POLISH_PROVIDER == ""
        assert reloaded.AI_POLISH_API_KEY == ""
        assert reloaded.AI_POLISH_MODEL == ""
    finally:
        monkeypatch.undo()
        importlib.reload(base_settings)


def test_the_test_settings_pin_the_polish_off_and_both_rate_tables_carry_its_scope(settings):
    """Tests never reach a vendor, and a polish request is never unthrottled: the scope
    needs a rate in development and in production, or the endpoint raises on every press."""
    assert settings.AI_POLISH_PROVIDER == ""
    assert settings.AI_POLISH_API_KEY == ""
    assert settings.AI_POLISH_MODEL == ""

    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["polish"] == "10/minute"

    # production.py is read as text: base is already imported under test, and importing
    # production would replace its settings. A comment must not satisfy the check.
    production = Path(base_settings.__file__).with_name("production.py")
    code_lines = [
        line for line in production.read_text().splitlines() if not line.lstrip().startswith("#")
    ]
    assert '"polish": "10/minute"' in "\n".join(code_lines)

    for name in ("anthropic", "httpx", "httpx2", "httpcore2"):
        assert settings.LOGGING["loggers"][name] == {"level": "WARNING", "propagate": False}


# ---- the endpoint -------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_throttle_cache():
    """The polish throttle is keyed by user pk in the local-memory cache, which nothing clears,
    and the rolled-back database reuses pk 1: without this the file's eleventh request is a 429."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def polish_sdk():
    with polish_builders.polish_sdk() as client_cls:
        yield client_cls


@dataclass
class Filer:
    client: APIClient
    session: IntakeSession


@pytest.fixture
def filer(user, above):
    client = APIClient()
    client.force_authenticate(user=user)
    return Filer(client, above)


def _polish_url(session):
    return f"/api/intake/sessions/{session.pk}/means-test/polish/"


def _post(filer, text=SENT):
    return filer.client.post(_polish_url(filer.session), {"explanation": text}, format="json")


def _create(client_cls, reply=None, error=None):
    create = client_cls.return_value.messages.create
    create.return_value = reply
    create.side_effect = error
    return create


def _stored(session):
    """Everything the means-test endpoint stores, read fresh, for a 'nothing changed' check."""
    record = MeansTestAnswers.objects.filter(session=session).first()
    return (
        None
        if record is None
        else (
            record.answers,
            record.debts_answered_on,
            record.next_spouse_vehicle_id,
            record.next_spouse_loan_id,
        ),
        list(SecuredDebtAnswers.objects.filter(debt__session=session).order_by("pk").values()),
    )


def test_a_rewrite_the_service_gives_comes_back_to_the_page(filer, polish_sdk):
    """The filer asks for a clearer version and gets the service's words back to review."""
    _create(polish_sdk, message(REWRITE))

    reply = _post(filer)

    assert reply.status_code == 200
    assert reply.json() == {"rewrite": REWRITE}
    assert polish_sdk.call_args.kwargs == {
        "api_key": "test-key",
        "base_url": BASE_URL,
        "timeout": 30.0,
        "max_retries": 0,
    }


def test_the_base_url_is_pinned_even_when_the_shell_sets_one(filer, polish_sdk, monkeypatch):
    """A shell that points the SDK at another host must not redirect a filer's words."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:4011")
    _create(polish_sdk, message(REWRITE))

    assert _post(filer).status_code == 200

    assert polish_sdk.call_args.kwargs["base_url"] == "https://api.anthropic.com"


def test_the_request_carries_only_the_explanation(filer, polish_sdk):
    """The service gets the box's words and the fixed instructions: none of the filer's own
    answers, name, email or session ride along."""
    create = _create(polish_sdk, message(REWRITE))

    assert _post(filer).status_code == 200

    sent = create.call_args.kwargs
    assert set(sent) == {"model", "max_tokens", "system", "messages", "output_config"}
    assert sent["messages"] == [{"role": "user", "content": SENT}]
    assert sent["system"] == SYSTEM_PROMPT
    # The session's pk is not checked: a small integer also stands in the prompt's rule numbers
    # and in "1,400".
    everything = repr(sent) + repr(polish_sdk.call_args.kwargs)
    for stored in (
        "Jane",
        "Doe",
        "testfiler",
        "filer@example.com",
        "jane.doe@example.com",
        "123 Main",
        "900-12-3456",
        "312-555-0100",
    ):
        assert stored not in everything


@pytest.mark.parametrize(
    ("text", "account"),
    [
        ("My number is 900-12-3456 on every form.", None),
        ("My number is 900123456 on every form.", None),
        ("Call me at 3125550100 after work.", None),
        ("Call me at 312 555 0100 after work.", None),
        ("Call me at (312) 555-0100 after work.", None),
        ("My old card, 4417 1234 5678, was closed in March.", "4417-1234-5678"),
        ("The bill came addressed to Doe in March.", None),
        ("Jane Doe was billed for the stay.", None),
        ("Write to jane.doe@example.com about the bill.", None),
        ("My login is testfiler and it was shared.", None),
        ("The bill went to 123 Main St last March.", None),
    ],
    ids=[
        "ssn_dashed",
        "ssn_bare",
        "phone_ten_digits",
        "phone_spaced",
        "phone_parenthesised",
        "account_four_four_four",
        "last_name",
        "full_name",
        "email",
        "username",
        "street_address",
    ],
)
def test_an_explanation_with_the_filers_identifier_is_refused_before_any_send(
    filer, polish_sdk, text, account
):
    """The filer's own identifiers never leave the server: the text is refused, not stripped,
    and no client is even built."""
    if account:
        complete_debt(filer.session, account_number=account)

    reply = _post(filer, text)

    assert reply.status_code == 400
    assert reply.json() == {"explanation": [MEANS_POLISH_IDENTIFIER]}
    polish_sdk.assert_not_called()


def test_a_session_with_no_debtor_info_is_checked_without_an_error(filer, polish_sdk):
    """A filer who has not reached the debtor step can still ask for a rewrite: there is no
    name to look for, and that is not an error."""
    filer.session.debtor_info.delete()
    _create(polish_sdk, message(REWRITE))

    assert _post(filer).status_code == 200


def test_a_relatives_first_name_a_creditors_name_and_two_dates_may_stay(filer, polish_sdk):
    """Facts about other people and dates are the substance of the explanation: only the
    filer's own identifiers are refused."""
    original = (
        "My sister Jane lent me money. I owe Demo Card Services. "
        "I paid on 2025-01-03 2025-02-10 and more later."
    )
    reply_text = (
        "My sister Jane lent me money, and I owe Demo Card Services. "
        "I paid on 2025-01-03 2025-02-10 and more later."
    )
    _create(polish_sdk, message(reply_text))

    reply = _post(filer, original)

    assert reply.status_code == 200
    assert reply.json() == {"rewrite": reply_text}


def test_a_missing_key_raises_at_use_and_check_passes_without_one(filer, caplog):
    """A key removed after the page loaded fails the press with one sentence, never the boot."""
    with override_settings(AI_POLISH_PROVIDER="anthropic", AI_POLISH_API_KEY=""):
        reply = _post(filer)

    assert reply.status_code == 503
    assert reply.json() == UNAVAILABLE
    assert "AI_POLISH_API_KEY" in caplog.text
    assert "test-key" not in caplog.text

    # The test settings' empty provider is refused first, so the log names the provider.
    caplog.clear()
    reply = _post(filer)
    assert reply.status_code == 503
    assert "AI_POLISH_PROVIDER" in caplog.text
    assert polish.configured() is False
    call_command("check")


def test_an_unknown_polish_provider_fails_the_request_not_the_boot(filer, caplog):
    """A misspelt provider must not take the site down, and a key pasted into the provider
    variable by mistake must not reach a log."""
    with override_settings(AI_POLISH_PROVIDER="gemini", AI_POLISH_API_KEY="k"):
        reply = _post(filer)
        assert polish.configured() is False

    assert reply.status_code == 503
    assert reply.json() == UNAVAILABLE
    assert "AI_POLISH_PROVIDER" in caplog.text
    assert "'gemini'" not in caplog.text


def test_the_page_hides_the_button_with_no_provider(filer, polish_sdk):
    """The page offers the rewrite only where a provider and key are set up."""
    url = f"/api/intake/sessions/{filer.session.pk}/means-test/"

    with override_settings(AI_POLISH_PROVIDER="", AI_POLISH_API_KEY=""):
        assert filer.client.get(url).json()["polish_available"] is False

    assert filer.client.get(url).json()["polish_available"] is True


def test_an_empty_reply_is_refused_not_re_sent(filer, polish_sdk, caplog):
    """A blank reply is one refusal, not a second send of the filer's words."""
    create = _create(polish_sdk, empty_message())

    reply = _post(filer)

    assert reply.status_code == 422
    assert reply.json() == NO_REWRITE
    assert create.call_count == 1
    assert "empty" in caplog.text


def test_a_refusal_is_not_retried_and_its_wording_is_not_kept(filer, polish_sdk, caplog):
    """A safety refusal is final: no second try, and whatever words it carried are the model's,
    not the filer's, and reach neither a log nor the filer."""
    refusal = refusal_message()
    refusal.content = [TextBlock(type="text", text="Demo refusal wording")]
    create = _create(polish_sdk, refusal)

    reply = _post(filer)

    assert reply.status_code == 422
    assert create.call_count == 1
    assert "Demo refusal wording" not in caplog.text
    assert reply.json() == NO_REWRITE


def test_a_reply_cut_off_at_max_tokens_is_refused(filer, polish_sdk, caplog):
    """A reply the model ran out of room to finish is half a thought, so it is not shown."""
    _create(polish_sdk, message(REWRITE, stop_reason="max_tokens"))

    reply = _post(filer)

    assert reply.status_code == 422
    assert reply.json() == NO_REWRITE
    assert "max_tokens" in caplog.text


@pytest.mark.parametrize("phrase", POLISH_PHRASES)
def test_a_rewrite_with_a_prohibited_phrase_never_reaches_the_filer(
    filer, polish_sdk, caplog, phrase
):
    """Nothing that reads as advice goes into a filer's sworn explanation, whoever wrote it."""
    _create(polish_sdk, message(f"{REWRITE} {phrase}."))

    reply = _post(filer)

    assert reply.status_code == 422
    assert phrase.casefold() not in caplog.text.casefold()
    assert phrase.casefold() not in reply.content.decode().casefold()


def test_a_filers_own_prohibited_phrase_is_refused_before_any_send(filer, polish_sdk):
    """The filer's own sentence "I recommend ..." is refused beside the box, so the service is
    never blamed for it and never sent it."""
    reply = _post(filer, f"{SENT} I recommend rest.")

    assert reply.status_code == 400
    assert reply.json() == {"explanation": [MEANS_POLISH_PHRASE]}
    polish_sdk.assert_not_called()


ADDED = [
    pytest.param(SENT, f"{REWRITE} It cost 2,000 more.", id="figure"),
    pytest.param(SENT, f"{REWRITE} On May 3 it changed.", id="dated_month"),
    pytest.param(
        NO_CLINIC,
        "My hours were cut in March 2025 and Demo Clinic billed 1,400 for the stay.",
        id="name",
    ),
    *(
        pytest.param(SENT, f"{REWRITE} {phrase}.", id=f"legal_{phrase}")
        for phrase in LEGAL_CONCLUSIONS
    ),
    pytest.param(
        SENT, f"{REWRITE} I declare under penalty of perjury that this is true.", id="oath"
    ),
]


@pytest.mark.parametrize(("original", "rewrite"), ADDED)
def test_a_rewrite_that_adds_a_figure_date_or_name_is_refused(
    filer, polish_sdk, caplog, original, rewrite
):
    """The service may reword the filer's account, never add to it."""
    _create(polish_sdk, message(rewrite))

    reply = _post(filer, original)

    assert reply.status_code == 422
    assert reply.json() == NO_REWRITE
    assert "added_facts" in caplog.text


@pytest.mark.parametrize(
    "rewrite",
    [
        "Demo explanation: my hours were cut in March 2025 and Demo Clinic billed me for the stay.",
        "Demo explanation: my hours were cut and Demo Clinic billed 1,400 for the stay.",
        "My explanation: my hours were cut in March 2025 and the clinic billed 1,400 for the stay.",
    ],
    ids=["figure", "month_and_year", "name"],
)
def test_a_rewrite_that_drops_a_figure_date_or_name_is_refused(filer, polish_sdk, caplog, rewrite):
    """A clearer explanation still holds every fact the filer wrote."""
    _create(polish_sdk, message(rewrite))

    reply = _post(filer)

    assert reply.status_code == 422
    assert reply.json() == NO_REWRITE
    assert "dropped_facts" in caplog.text


@pytest.mark.parametrize(
    ("rewrite", "reason"),
    [
        (
            "Since March 2025 I pay 1,400 monthly to Demo Clinic for my illness care.",
            "too_short",
        ),
        ("I'm sorry, but I can't rewrite this.", "dropped_facts"),
    ],
    ids=["keeps_every_fact", "refusal_prose"],
)
def test_a_rewrite_under_half_the_length_is_refused(filer, polish_sdk, caplog, rewrite, reason):
    """A paragraph squeezed to a line is not the filer's explanation. Every reason is the same
    422 to the filer, so the reason is read from the log."""
    _create(polish_sdk, message(rewrite))

    reply = _post(filer, POLISH_DEMO_EXPLANATION)

    assert reply.status_code == 422
    assert reply.json() == NO_REWRITE
    assert reason in caplog.text


@pytest.mark.parametrize(
    ("original", "rewrite"),
    [
        (SENT, REWRITE.replace("1,400", "1400")),
        (SENT, REWRITE),
        (
            "My hours were cut in March 2025. I acted in good faith when Demo Clinic billed 1,400.",
            "In March 2025 my hours were cut. I acted in good faith when Demo Clinic billed 1,400.",
        ),
        (
            NO_CLINIC,
            "My hours were cut in March 2025 and the lab billed 1,400 for the stay, "
            "which may take years to pay.",
        ),
        (
            "I am behind. Since March 2025 I pay 1,400 to the lab for the stay.",
            "I'm behind. Since March 2025 I pay 1,400 to the lab for the stay.",
        ),
    ],
    ids=["comma_in_figure", "name_in_both", "legal_phrase_the_filer_wrote", "may_added", "i_am"],
)
def test_a_rewrite_that_keeps_the_filers_facts_passes(filer, polish_sdk, original, rewrite):
    """Wording changes are the point: only a change to the facts is refused."""
    _create(polish_sdk, message(rewrite))

    reply = _post(filer, original)

    assert reply.status_code == 200
    assert reply.json() == {"rewrite": rewrite}


def test_refused_items_reach_no_log_and_no_reply(filer, polish_sdk, caplog):
    """The names and figures a refusal found are the filer's or the model's words: the log
    holds one word and the filer gets one sentence."""
    _create(
        polish_sdk,
        message("My hours were cut in March 2025 and Demo Clinic 7,777 billed 1,400 for the stay."),
    )

    reply = _post(filer, NO_CLINIC)

    assert reply.status_code == 422
    for record in caplog.records:
        assert "Demo Clinic" not in record.getMessage()
        assert "7,777" not in record.getMessage()
    assert "Demo Clinic" not in caplog.text
    assert "Demo Clinic" not in reply.content.decode()
    assert "7,777" not in reply.content.decode()


@pytest.mark.parametrize(
    ("rewrite", "reason"),
    [
        ("\n".join(["line"] * 37), "unprintable"),
        (f"{REWRITE} □", "unprintable"),
        ("a" * 2001, "too_long"),
    ],
    ids=["37_lines", "a_box_character", "2001_characters"],
)
def test_a_rewrite_that_cant_print_whole_is_refused_before_review(
    filer, polish_sdk, caplog, rewrite, reason
):
    """A rewrite the form can't print would fail later, after the filer approved it, so it is
    refused now, and nothing is stored."""
    answer_means_test(filer.session)
    before = _stored(filer.session)
    _create(polish_sdk, message(rewrite))

    reply = _post(filer)

    assert reply.status_code == 422
    assert reply.json() == NO_REWRITE
    assert reason in caplog.text
    assert _stored(filer.session) == before


def _request(**headers):
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages", headers=headers)


def _status_error(cls, status):
    response = httpx2.Response(status, request=_request())
    return cls("req_demo_123 Demo Clinic 7,777", response=response, body=None)


SDK_ERRORS = [
    APITimeoutError(_request(**{"request-id": "req_demo_123"})),
    APIConnectionError(message="Connection error.", request=_request(**{"x-id": "req_demo_123"})),
    _status_error(RateLimitError, 429),
    _status_error(InternalServerError, 500),
]


@pytest.mark.parametrize("error", SDK_ERRORS, ids=lambda error: type(error).__name__)
def test_a_timeout_or_network_failure_leaves_the_draft_with_one_sentence(
    filer, polish_sdk, caplog, error
):
    """The service being down changes nothing for the filer but one sentence, and the vendor's
    request id and message never reach a log."""
    _create(polish_sdk, error=error)

    reply = _post(filer)

    assert reply.status_code == 503
    assert reply.json() == UNAVAILABLE
    assert type(error).__name__ in caplog.text
    assert "req_demo_123" not in caplog.text
    assert "Demo Clinic" not in caplog.text


PINNED_LOGGERS = ("anthropic", "httpx", "httpx2", "httpcore2")


def _nothing_reaches_caplog(caplog):
    """A pinned logger has no handler and does not propagate, so a record goes nowhere."""
    for name in PINNED_LOGGERS:
        logger = logging.getLogger(name)
        assert logger.propagate is False
        assert logger.handlers == []
        with caplog.at_level(logging.DEBUG):
            logger.debug("%s", SENT)
            logger.warning("%s", SENT)
        assert SENT not in caplog.text


def test_a_polish_request_is_audited_without_its_text(filer, polish_sdk, caplog, monkeypatch):
    """The audit trail shows that a polish request happened and how it ended, and holds none of
    the filer's words or the service's."""
    _create(polish_sdk, message(REWRITE))
    path = _polish_url(filer.session)
    caplog.set_level(logging.DEBUG)

    assert _post(filer).status_code == 200

    row = AuditLog.objects.filter(action=f"POST {path}").get()
    assert row.upl_sensitive is True
    assert row.details["status_code"] == 200
    audited = json.dumps(model_to_dict(row), default=str)
    for text in (SENT, REWRITE):
        assert text not in audited
        assert text not in caplog.text

    # Behaviour, not level: the SDK's own setup_logging() sets the level at import, so a level
    # assertion would depend on test order. With the loggers pinned, nothing reaches a handler.
    _nothing_reaches_caplog(caplog)

    # ANTHROPIC_LOG=debug turns the SDK's request logging on; the pin must still hold.
    from anthropic._utils import _logs

    monkeypatch.setenv("ANTHROPIC_LOG", "debug")
    levels = {name: logging.getLogger(name).level for name in PINNED_LOGGERS}
    root = logging.getLogger()
    handlers = list(root.handlers)
    try:
        _logs.setup_logging()
        assert logging.getLogger("anthropic").level == logging.DEBUG
        _nothing_reaches_caplog(caplog)
    finally:
        for name, level in levels.items():
            logging.getLogger(name).setLevel(level)
        root.handlers[:] = handlers


def test_a_polish_request_writes_nothing_and_never_reopens_a_completed_intake(filer, polish_sdk):
    """Asking for a rewrite is not an edit: the stored answers stand and a completed intake
    stays completed until the filer approves and saves something."""
    answer_means_test(filer.session)
    before = _stored(filer.session)
    assert IntakeSession.objects.get(pk=filer.session.pk).status == "completed"
    _create(polish_sdk, message(REWRITE))

    assert _post(filer).status_code == 200

    assert _stored(filer.session) == before
    assert IntakeSession.objects.get(pk=filer.session.pk).status == "completed"


def test_another_filers_session_is_not_found(filer, polish_sdk):
    """One filer's words can't be sent through another filer's session."""
    other = User.objects.create_user(username="otherfiler", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=other)

    reply = client.post(_polish_url(filer.session), {"explanation": SENT}, format="json")

    assert reply.status_code == 404
    polish_sdk.assert_not_called()


def test_polish_is_throttled_in_its_own_scope(filer, polish_sdk, settings):
    """Every press costs money and sends a filer's words out, so the endpoint has its own rate,
    apart from the ordinary per-user one."""
    from apps.intake.views import IntakeSessionViewSet

    assert PolishThrottle.scope == "polish"
    assert IntakeSessionViewSet.polish.kwargs["throttle_classes"] == [PolishThrottle]
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["polish"] == "10/minute"
    _create(polish_sdk, message(REWRITE))

    codes = [_post(filer).status_code for _ in range(11)]

    assert codes == [200] * 10 + [429]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"explanation": SENT, "amount": "10.00"}, {"amount": [NOT_A_MEANS_ANSWER]}),
        ({}, {"explanation": [MEANS_POLISH_BLANK]}),
        ({"explanation": None}, {"explanation": [MEANS_POLISH_BLANK]}),
        ({"explanation": "  "}, {"explanation": [MEANS_POLISH_BLANK]}),
        ({"explanation": "a" * 2001}, {"explanation": [MEANS_EXPLANATION_TOO_LONG]}),
    ],
    ids=["second_key", "no_explanation", "null", "blank", "too_long"],
)
def test_a_body_with_a_second_key_or_no_explanation_is_refused(filer, polish_sdk, body, expected):
    """The endpoint takes the box's words and nothing else, and says in plain words what is
    wrong with a body that is not that."""
    reply = filer.client.post(_polish_url(filer.session), body, format="json")

    assert reply.status_code == 400
    assert reply.json() == expected
    polish_sdk.assert_not_called()


def test_an_unexpected_failure_logs_its_type_and_none_of_its_text(filer, polish_sdk, caplog):
    """A bug of ours mid-request still gives the filer one sentence, and its message, which may
    quote the filer's words, never reaches a log: only the exception's type does."""
    _create(polish_sdk, error=RuntimeError("Demo Clinic 7,777"))

    reply = _post(filer)

    assert reply.status_code == 503
    assert reply.json() == UNAVAILABLE
    assert "RuntimeError" in caplog.text
    assert "Demo Clinic" not in caplog.text
    assert "7,777" not in caplog.text
