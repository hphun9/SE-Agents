"""
Secretary Agent — natural-language smart dispatcher

Chat in plain language; the Secretary uses Haiku to classify your intent and
automatically routes to the right specialist.  No need to know role names.

Examples
--------
  /s I need help choosing between PostgreSQL and MongoDB
  → 🏗️ Solution Architect answers

  /s how do I structure unit tests for async functions?
  → 🧪 QA Engineer answers

  /s who handles deployment and Docker stuff?
  → 🤖 Secretary: "That's DevOps — use /ask devops <question>"

  /s what agents are on the team?
  → 🤖 Secretary: lists the full team roster
"""

from __future__ import annotations
from config import MODELS
from core.claude import call_claude, parse_json
from core.models import ProjectSession
from agents.consult import consult_agent, _ROLES

# ─── Prompts ─────────────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = """\
You are a smart dispatcher for an AI software-development team.
Read the user's message and decide which specialist should answer it.

Specialists and their domains:
  ba        — requirements, user stories, BRD, scope, stakeholders, product definition
  sa        — system design, tech-stack choice, database schema, architecture trade-offs
  pm        — timelines, sprints, milestones, risk, resource and delivery planning
  lead      — code review, API design, engineering standards, technical decisions
  dev       — backend code, server logic, REST/GraphQL APIs, auth, databases, debugging
  frontend  — UI components, React/Vue/Angular, CSS/Tailwind, state management, UX
  qa        — test cases, testing strategy, test automation, bug reproduction, quality

Use null when:
  • The message is a greeting or small-talk
  • The user is asking meta questions ("who does X?", "what agents exist?")
  • No specialist is clearly a better fit than any other

Return ONLY valid JSON — no prose, no markdown:
{"role": "<key or null>", "reason": "<one sentence>"}"""

_SECRETARY_SYSTEM = """\
You are a friendly, knowledgeable AI secretary for a software-development team.
Your job is to help users understand who on the team can help them, answer
general software questions, and introduce the team's capabilities.

The team you support:
  • Business Analyst  (ba)       — requirements, user stories, scope
  • Solution Architect (sa)      — system design, tech stack, architecture
  • Project Manager   (pm)       — timelines, milestones, risk planning
  • Tech Lead         (lead)     — code review, API design, engineering standards
  • Backend Developer (dev)      — APIs, databases, server-side code
  • Frontend Developer (frontend)— UI, React/Vue, CSS, UX
  • QA Engineer       (qa)       — testing strategy, test cases, automation

Keep answers concise and helpful.
When a specialist is the better choice, say so and tell the user they can
reach them with /ask <role> <question> or just /s <question> (you will route it)."""

# ─── Role display metadata (emoji + specialty blurb) ─────────────────────────

_ROLE_META: dict[str, tuple[str, str]] = {
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
    Classify the user's message with Haiku, route to the right specialist,
    and return their response.

    Returns
    -------
    {
        "routed_to":  str,   # role key (e.g. "sa") or "secretary"
        "role_name":  str,   # human-readable label
        "emoji":      str,   # role emoji
        "response":   str,   # the actual answer
        "reason":     str,   # why this role was chosen (for logging)
    }
    """
    # ── Step 1: classify intent (Haiku — cheap + fast) ────────────────────────
    raw = await call_claude(
        MODELS["ba_chat"],          # Haiku
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

    # ── Step 2a: route to specialist ─────────────────────────────────────────
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

    # ── Step 2b: answer directly as secretary (meta / general questions) ──────
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
