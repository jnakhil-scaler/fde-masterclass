import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

_client = None


def has_real_api_key() -> bool:
    """Distinguishes a real Anthropic key from the .env.example placeholder
    ('sk-ant-...', 10 chars) so tests skip cleanly instead of failing with
    an auth error when only the placeholder is present."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return len(key) > 20 and key.startswith("sk-ant-")


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def call_with_tool(system: str, user_message: str, tool_schema: dict) -> dict:
    """Send a single-tool request and return the tool_use input dict."""
    client = get_client()
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("Claude did not return a tool_use block")
