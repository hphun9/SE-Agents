"""
Claude wrapper — routes calls through the `claude` CLI so they use
your Max subscription instead of direct API credits.

Requires the `claude` CLI to be installed and authenticated:
  https://claude.ai/code
"""

from __future__ import annotations
import asyncio
import json
import re


async def call_claude(
    model: str,
    system: str,
    messages: list[dict],
    max_tokens: int = 16_000,   # kept for signature compatibility; CLI uses its own default
) -> str:
    """Call Claude via `claude -p` and return the text response."""
    parts: list[str] = []
    if system:
        parts.append(system)

    for msg in messages:
        role = "Human" if msg["role"] == "user" else "Assistant"
        content = msg["content"]
        if isinstance(content, list):
            # Flatten content-block arrays (e.g. from multi-turn BA history)
            content = " ".join(
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        parts.append(f"{role}: {content}")

    full_prompt = "\n\n".join(parts)

    proc = await asyncio.create_subprocess_exec(
        "claude", "-p", full_prompt, "--model", model,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err = stderr.decode().strip()
        raise RuntimeError(f"claude CLI error (model={model}): {err}")

    # Strip ANSI escape codes in case the CLI emits them
    text = stdout.decode()
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    return text.strip()


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
