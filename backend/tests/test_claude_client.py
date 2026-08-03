from app.agents.claude_client import has_real_api_key

# No module-level pytestmark here: this test exercises pure string logic with
# zero network dependency, so it must always run (never skip) regardless of
# whether a real ANTHROPIC_API_KEY is present. Keeping it out of
# test_agent_cleaning.py (which has a module-level skipif) is what makes that
# possible.


def test_has_real_api_key_logic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-...")
    assert has_real_api_key() is False  # placeholder, too short

    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert has_real_api_key() is False  # empty

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-" + "x" * 30)
    assert has_real_api_key() is True  # long enough, right prefix

    monkeypatch.setenv("ANTHROPIC_API_KEY", "wrong-prefix-" + "x" * 30)
    assert has_real_api_key() is False  # long enough but wrong prefix
