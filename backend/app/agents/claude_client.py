"""LLM client for the agent pipeline, routed through OpenRouter.

OpenRouter (https://openrouter.ai) exposes an OpenAI-compatible Chat
Completions endpoint rather than Anthropic's native Messages API, so this
module talks to it via the `openai` SDK pointed at OpenRouter's base_url,
requesting the `anthropic/claude-sonnet-5` model slug. The public interface
(`has_real_api_key`, `get_client`, `call_with_tool`) is unchanged from the
original direct-Anthropic implementation, so the 4 agent modules that import
it (cleaning, credit_risk, order_parser, demand_forecast) did not need any
changes.

See `claude_client_anthropic_native.py` for the original direct-Anthropic
implementation, preserved for reference (currently unused/dead code).
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = None

OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-5")
OPENROUTER_MODEL_FAST = os.environ.get("OPENROUTER_MODEL_FAST", "anthropic/claude-haiku-4.5")


def has_real_api_key() -> bool:
    """Distinguishes a real OpenRouter key from the .env.example placeholder
    ('sk-or-v1-...', 12 chars) so tests skip cleanly instead of failing with
    an auth error when only the placeholder is present. Real OpenRouter keys
    are much longer and share the same 'sk-or-v1-' prefix as the placeholder,
    so length is what actually distinguishes them."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    return len(key) > 20 and key.startswith("sk-or-v1-")


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )
    return _client


def call_with_tool(system: str, user_message: str, tool_schema: dict, model: str = None) -> dict:
    """Send a single-tool request and return the parsed tool-call arguments dict.

    `model` defaults to OPENROUTER_MODEL (Sonnet) if not given. Pass
    OPENROUTER_MODEL_FAST (Haiku) explicitly for high-volume, low-complexity
    calls where cost matters more than squeezing out marginal accuracy."""
    client = get_client()
    tool_name = tool_schema["name"]
    response = client.chat.completions.create(
        model=model or OPENROUTER_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        tools=[{
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_schema.get("description", ""),
                "parameters": tool_schema["input_schema"],
            },
        }],
        tool_choice={"type": "function", "function": {"name": tool_name}},
    )
    if not response.choices:
        raise ValueError(f"OpenRouter returned no choices for tool {tool_name!r}")
    message = response.choices[0].message
    if not message.tool_calls:
        raise ValueError(f"Model did not return a tool call for {tool_name!r}")
    raw_arguments = message.tool_calls[0].function.arguments
    try:
        return json.loads(raw_arguments)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Model returned malformed JSON for tool {tool_name!r}: {e}\nRaw: {raw_arguments!r}"
        ) from e
