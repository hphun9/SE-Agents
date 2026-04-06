"""
Async Claude API wrapper.

Uses streaming + get_final_message() to handle large outputs without timeout.
Adaptive thinking is enabled for Sonnet/Opus only (not Haiku).
"""

from __future__ import annotations
import json
import re
import anthropic
from config import THINKING_MODELS

_client = anthropic.AsyncAnthropic()


async def call_claude(
    model: str,
    system: str,
    messages: list[dict],
    max_tokens: int = 16_000,
) -> str:
    """Call Claude and return the text response."""
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    if model in THINKING_MODELS:
        kwargs["thinking"] = {"type": "adaptive"}

    async with _client.messages.stream(**kwargs) as stream:
        response = await stream.get_final_message()

    for block in response.content:
        if block.type == "text":
            return block.text

    raise ValueError(f"Claude ({model}) returned no text content")


def parse_json(raw: str) -> dict:
    """
    Extract and parse JSON from a Claude response.
    Handles markdown code fences and leading/trailing prose.
    """
    cleaned = raw.strip()

    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # Advance to first { or [
    first_brace   = cleaned.find("{")
    first_bracket = cleaned.find("[")

    if first_brace == -1 and first_bracket == -1:
        raise ValueError("No JSON object found in Claude response")

    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start = first_brace
    else:
        start = first_bracket

    cleaned = cleaned[start:]

    # Find matching closing delimiter
    open_c  = cleaned[0]
    close_c = "}" if open_c == "{" else "]"
    depth, end = 0, -1
    in_string = False
    escape_next = False

    for i, ch in enumerate(cleaned):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_c:
            depth += 1
        elif ch == close_c:
            depth -= 1
            if depth == 0:
                end = i
                break

    if end != -1:
        cleaned = cleaned[: end + 1]

    return json.loads(cleaned)
