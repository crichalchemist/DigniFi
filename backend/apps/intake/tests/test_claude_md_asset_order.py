import pytest
from django.conf import settings


def _claude_md_text():
    path = settings.BASE_DIR.parent / "CLAUDE.md"
    if not path.is_file():
        pytest.skip("the repo's CLAUDE.md isn't here (compose's backend mounts backend/ only)")
    return path.read_text()


def test_claude_md_tells_agents_that_assets_read_by_id_and_debts_by_creditor():
    # An agent trusting a stale "every other read keeps model order" would expect assets
    # in a model order that AssetInfo no longer has (3b removed Meta.ordering).
    text = _claude_md_text()
    assert "every other read keeps model order" not in text
    assert "every other read of assets goes by id" in text
    assert "debts keep model order" not in text
    assert "a session read lists debts by creditor name" in text


def test_claude_md_says_pre_3f_refusals_come_after_the_assets_check():
    # Every pre-3f persona is also pre-3b and completed, so _prepare raises AssetStepGap
    # before Form 101's or 103B's requires runs; an agent must not expect the /filing-fee link first.
    text = _claude_md_text()
    assert "so their Form 101 is refused with a link to `/filing-fee`" not in text
    assert "so their 103B is refused instead." not in text
    assert "once the Assets step's check passes their Form 101 is refused" in text
    assert "so Complete and every forms call refuse them" not in text
    assert "the packet list never runs that check" in text


def test_the_docs_check_skips_where_compose_mounts_only_backend(tmp_path, settings):
    # Under compose the backend is /app and its parent holds no CLAUDE.md: the docs test
    # must skip there, not error, or the documented fast run fails.
    settings.BASE_DIR = tmp_path / "app"
    with pytest.raises(pytest.skip.Exception):
        _claude_md_text()
