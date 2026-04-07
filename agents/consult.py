"""
Direct agent consultation.

Lets the user address any role directly via /ask:
  /ask ba  What requirements am I missing?
  /ask dev Fix the auth bug — here's the error: ...
  /ask qa  Write unit tests for the login flow

Agents respond in natural language (not JSON) and pull relevant
documents from the active session as context.
"""

from __future__ import annotations
import json
from config import MODELS, HAIKU, SONNET, OPUS
from core.claude import call_claude
from core.models import ProjectSession

# ─── Role registry ───────────────────────────────────────────────────────────

_ROLES: dict[str, dict] = {
    "ba": {
        "name":   "Business Analyst",
        "emoji":  "🔍",
        "model":  SONNET,
        "system": (
            "You are a senior Business Analyst. Help the user refine requirements, "
            "identify gaps, clarify scope, and write user stories. "
            "Respond in clear, concise natural language. Use bullet points where helpful."
        ),
        "context_keys": ["brd"],
    },
    "sa": {
        "name":   "Solution Architect",
        "emoji":  "🏗️",
        "model":  OPUS,
        "system": (
            "You are a senior Solution Architect. Help the user make architecture decisions, "
            "evaluate trade-offs, design system components, and review technical designs. "
            "Respond in clear, concise natural language."
        ),
        "context_keys": ["brd", "architecture"],
    },
    "pm": {
        "name":   "Project Manager",
        "emoji":  "📅",
        "model":  SONNET,
        "system": (
            "You are a senior Project Manager. Help the user with sprint planning, "
            "risk identification, timeline estimation, and delivery strategy. "
            "Respond in clear, concise natural language."
        ),
        "context_keys": ["brd", "project_plan"],
    },
    "lead": {
        "name":   "Tech Lead",
        "emoji":  "⚙️",
        "model":  OPUS,
        "system": (
            "You are a senior Tech Lead. Help the user with code reviews, technical decisions, "
            "API design, system integration, and engineering standards. "
            "Respond in clear, concise natural language. Include code snippets when useful."
        ),
        "context_keys": ["architecture", "tech_spec"],
    },
    "dev": {
        "name":   "Backend Developer",
        "emoji":  "🔧",
        "model":  OPUS,
        "system": (
            "You are a senior Backend Developer. Help the user write, debug, and review "
            "backend code. Provide working code examples, explain errors, and suggest fixes. "
            "Include code blocks with language tags."
        ),
        "context_keys": ["tech_spec", "backend_impl"],
    },
    "frontend": {
        "name":   "Frontend Developer",
        "emoji":  "🎨",
        "model":  SONNET,
        "system": (
            "You are a senior Frontend Developer. Help the user with UI components, "
            "state management, styling, and browser APIs. "
            "Provide working code examples with proper syntax."
        ),
        "context_keys": ["tech_spec", "frontend_impl"],
    },
    "qa": {
        "name":   "QA Engineer",
        "emoji":  "🧪",
        "model":  SONNET,
        "system": (
            "You are a senior QA Engineer. Help the user write test cases, debug test failures, "
            "design test strategies, and improve test coverage. "
            "Include test code examples when relevant."
        ),
        "context_keys": ["tech_spec", "backend_impl", "frontend_impl", "qa_plan"],
    },
}

# Aliases mapping user-typed shorthand → canonical key
_ALIASES: dict[str, str] = {
    "ba":           "ba",
    "business":     "ba",
    "analyst":      "ba",
    "sa":           "sa",
    "architect":    "sa",
    "architecture": "sa",
    "pm":           "pm",
    "manager":      "pm",
    "lead":         "lead",
    "tech_lead":    "lead",
    "techlead":     "lead",
    "tl":           "lead",
    "dev":          "dev",
    "backend":      "dev",
    "be":           "dev",
    "frontend":     "frontend",
    "fe":           "frontend",
    "ui":           "frontend",
    "qa":           "qa",
    "test":         "qa",
    "tester":       "qa",
}

_CONTEXT_LIMIT = 3000   # chars per context doc


# ─── Public API ──────────────────────────────────────────────────────────────

def resolve_role(raw: str) -> str | None:
    """Return canonical role key or None if not recognised."""
    return _ALIASES.get(raw.lower().strip())


async def consult_agent(
    role_key: str,
    question: str,
    session: ProjectSession | None,
) -> str:
    """Call the named agent with the user's question and optional session context."""
    role = _ROLES[role_key]
    messages: list[dict] = []

    # Inject relevant session documents as context
    if session:
        context_parts: list[str] = []
        for key in role["context_keys"]:
            doc = getattr(session, key, None)
            if doc:
                snippet = json.dumps(doc)[:_CONTEXT_LIMIT]
                context_parts.append(f"[{key.upper()}]\n{snippet}")
        if context_parts:
            messages.append({
                "role": "user",
                "content": "Here is context from the current project:\n\n" + "\n\n".join(context_parts),
            })
            messages.append({
                "role": "assistant",
                "content": "Got it — I've reviewed the project context. What do you need?",
            })

    messages.append({"role": "user", "content": question})

    return await call_claude(role["model"], role["system"], messages)


def list_roles() -> str:
    """Return a formatted string of available roles for help text."""
    lines = []
    for key, r in _ROLES.items():
        aliases = [a for a, k in _ALIASES.items() if k == key and a != key]
        alias_str = f" \\(also: {', '.join(aliases[:2])}\\)" if aliases else ""
        lines.append(f"{r['emoji']} `{key}`{alias_str} — {r['name']}")
    return "\n".join(lines)
