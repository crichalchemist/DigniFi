import pytest
from django.conf import settings


def _claude_md_text():
    path = settings.BASE_DIR.parent / "CLAUDE.md"
    if not path.is_file():
        pytest.skip("the repo's CLAUDE.md isn't here (compose's backend mounts backend/ only)")
    return path.read_text()


def test_claude_md_tells_agents_that_assets_read_by_id_and_debts_in_model_order():
    # An agent trusting a stale "every other read keeps model order" would expect assets
    # in a model order that AssetInfo no longer has (3b removed Meta.ordering).
    text = _claude_md_text()
    assert "every other read keeps model order" not in text
    assert "every other read of assets goes by id" in text
    assert "debts keep model order" in text


def test_the_docs_check_skips_where_compose_mounts_only_backend(tmp_path, settings):
    # Under compose the backend is /app and its parent holds no CLAUDE.md: the docs test
    # must skip there, not error, or the documented fast run fails.
    settings.BASE_DIR = tmp_path / "app"
    with pytest.raises(pytest.skip.Exception):
        _claude_md_text()
