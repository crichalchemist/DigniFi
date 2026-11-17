"""The line 43 AI polish: a filer's words go to a hosted service only by deliberate setup.

This module starts with the settings that gate it. The endpoint's tests arrive with the
endpoint.
"""

import importlib
from pathlib import Path

import environ

import config.settings.base as base_settings


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
