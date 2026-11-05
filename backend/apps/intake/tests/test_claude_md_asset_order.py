from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_claude_md_tells_agents_that_assets_read_by_id_and_debts_in_model_order():
    # An agent trusting a stale "every other read keeps model order" would expect assets
    # in a model order that AssetInfo no longer has (3b removed Meta.ordering).
    text = (REPO_ROOT / "CLAUDE.md").read_text()
    assert "every other read keeps model order" not in text
    assert "every other read of assets goes by id" in text
    assert "debts keep model order" in text
