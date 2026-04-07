"""
Secretary Agent — natural-language smart dispatcher

The Secretary is the front door of the system.  Every plain-text message
goes through it first so the user never has to know role names or commands.

Classification outcomes
-----------------------
  "project"   → the message describes a software project to build
                → orchestrator starts the full BA→SA→PM→TL→Dev→QA pipeline

  specialist  → the message is a technical question for ba / sa / pm /
                lead / dev / frontend / qa
                → routed to that agent, answered immediately

  null        → greeting, small-talk, meta question ("what can you do?")
                → Secretary answers directly

Examples
--------
  "Hi"
  → 🤖 Secretary: "Hi! Tell me about a project or ask /s <anything>"

  "Build me a SaaS app for managing invoices"
  → 🚀 Pipeline starts (BA takes over)

  "What's the difference between REST and GraphQL?"
  → 🏗️ Solution Architect answers

  "How do I write async unit tests in Python?"
  → 🧪 QA Engineer answers

  "Who handles Docker and CI/CD?"
  → 🤖 Secretary answers directly
"""

from __future__ import annotations
from config import MODELS
from core.claude import call_claude, parse_json
from core.models import ProjectSession
from agents.consult import consult_agent, _ROLES

# ─── Prompts ─────────────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = """\
You are a smart dispatcher for an AI software-development team.
Read the user's message and classify it into exactly one category.

FIRST — is this a SOFTWARE PROJECT REQUEST?
A project request asks to BUILD or CREATE something:
  "Build me a SaaS app for managing invoices"
  "Create a REST API for a food delivery platform"
  "I need a React dashboard with user authentication"
  "Make a mobile app for expense tracking"
  "Develop an e-commerce website"
If yes → return role = "project"

SECOND — is this a specific technical QUESTION for a specialist?
  ba        — requirements, user stories, BRD, scope, stakeholders
  sa        — system design, tech-stack choice, DB schema, architecture trade-offs
  pm        — timelines, sprints, milestones, risk, delivery planning
  lead      — code review, API design, engineering standards, technical decisions
  dev       — backend code, server logic, APIs, auth, databases, debugging
  frontend  — UI components, React/Vue/Angular, CSS, state management, UX
  qa        — test cases, testing strategy, automation, quality assurance
If yes → return the specialist key

THIRD — for everything else (greetings, small-talk, meta questions, unclear):
→ return null

Return ONLY valid JSON — no prose, no markdown fences:
{"role": "<project|specialist_key|null>", "reason": "<one sentence>"}"""

_SECRETARY_SYSTEM = """\
You are a friendly AI secretary for a software-development team.
Greet the user warmly and explain what the team can do for them.
Keep it short — 2-3 sentences max.

The team can:
• Build full software projects end-to-end (just describe your idea)
• Answer technical questions instantly (BA, SA, PM, Tech Lead, Dev, Frontend, QA)
• Fix bugs in existing code (/fix command)

Hint at how to use the bot naturally without listing every command.

IMPORTANT: Always respond in the same language the user writes in.
If they write in Vietnamese → respond in Vietnamese.
If they write in English → respond in English.
Match their language exactly."""

# ─── Role display metadata ────────────────────────────────────────────────────

_ROLE_META: dict[str, tuple[str, str, str]] = {
    "ba":       ("🔍", "Business Analyst",   "requirements, user stories, scope"),
    "sa":       ("🏗️", "Solution Architect", "system design, tech stack, architecture"),
    "pm":       ("📅", "Project Manager",    "timelines, milestones, risk planning"),
    "lead":     ("⚙️", "Tech Lead",          "code review, API design, engineering standards"),
    "dev":      ("🔧", "Backend Developer",  "APIs, databases, server-side code"),
    "frontend": ("🎨", "Frontend Developer", "UI, React/Vue, CSS, UX"),
    "qa":       ("🧪", "QA Engineer",        "testing strategy, test cases, automation"),
}


# ─── Public API ──────────────────────────────────────────────────────────────

async def secretary_dispatch(
    message: str,
    session: ProjectSession | None = None,
) -> dict:
    """
    Classify the user's message and route it appropriately.

    Returns
    -------
    {
        "routed_to":  "project" | role_key | "secretary"
        "role_name":  str    — human-readable label
        "emoji":      str    — role emoji
        "response":   str    — answer (empty string when routed_to == "project")
        "reason":     str    — why this classification was chosen
    }
    """
    # ── Step 1: classify intent with Haiku (cheap + fast) ────────────────────
    raw = await call_claude(
        MODELS["ba_chat"],
        _CLASSIFY_SYSTEM,
        [{"role": "user", "content": message}],
        max_tokens=150,
    )
    try:
        classified = parse_json(raw)
        role_key = classified.get("role")
        reason   = classified.get("reason", "")
    except Exception:
        role_key = None
        reason   = "classification failed"

    # ── Step 2a: it's a project — signal the caller to start the pipeline ────
    if role_key == "project":
        return {
            "routed_to": "project",
            "role_name": "Pipeline",
            "emoji":     "🚀",
            "response":  "",
            "reason":    reason,
        }

    # ── Step 2b: route to specialist ─────────────────────────────────────────
    if role_key and role_key in _ROLES:
        emoji, role_name, _ = _ROLE_META.get(role_key, ("🤖", role_key, ""))
        response = await consult_agent(role_key, message, session)
        return {
            "routed_to": role_key,
            "role_name": role_name,
            "emoji":     emoji,
            "response":  response,
            "reason":    reason,
        }

    # ── Step 2c: answer directly as secretary (greeting / meta / unclear) ────
    response = await call_claude(
        MODELS["ba_chat"],
        _SECRETARY_SYSTEM,
        [{"role": "user", "content": message}],
    )
    return {
        "routed_to": "secretary",
        "role_name": "Secretary",
        "emoji":     "🤖",
        "response":  response,
        "reason":    reason,
    }


def team_roster() -> str:
    """Return a formatted team roster (MarkdownV2-safe)."""
    lines = []
    for key, (emoji, name, specialty) in _ROLE_META.items():
        lines.append(f"{emoji} *{name}* \\(`{key}`\\) — {specialty}")
    return "\n".join(lines)
