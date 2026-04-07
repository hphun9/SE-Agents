"""
Business Analyst Agent

Model strategy:
  - Clarification questions  → Haiku  (fast, cheap Q&A)
  - Final BRD production     → Sonnet (structured document)

Conducts up to MAX_BA_ROUNDS rounds of clarification then produces the BRD.
"""

from __future__ import annotations
from config import MODELS, MAX_BA_ROUNDS
from core.claude import call_claude, parse_json
from core.models import ProjectSession

# ─── System Prompt ───────────────────────────────────────────────────────────

_SYSTEM = f"""You are a senior Business Analyst AI. Your job is to gather software requirements and produce a formal Business Requirements Document (BRD).

RULES:
- If critical information is missing, ask the most important clarifying questions (max 5 per round).
- After sufficient clarification (1-3 rounds), produce the BRD.
- After round {MAX_BA_ROUNDS}, produce the BRD regardless using reasonable assumptions.
- ALWAYS write your "analysis", "questions", and "context" fields in the same language the user writes in. If they write in Vietnamese, those fields must be in Vietnamese. If English, use English.

OUTPUT: Respond with ONLY valid JSON — no prose, no markdown fences.

When you need more information:
{{
  "status": "NEEDS_CLARIFICATION",
  "analysis": "<what you understand so far>",
  "questions": ["<question 1>", "<question 2>"],
  "context": "<why these questions matter>",
  "iteration": <round number>
}}

When requirements are clear (produce the BRD):
{{
  "status": "REQUIREMENTS_COMPLETE",
  "brd": {{
    "title": "<project title>",
    "overview": "<2-3 sentence overview>",
    "problem_statement": "<core problem being solved>",
    "goals": ["<goal 1>"],
    "functional_requirements": [
      {{"id": "FR-001", "title": "<name>", "description": "<detail>", "priority": "MUST|SHOULD|COULD|WONT"}}
    ],
    "non_functional_requirements": [
      {{"category": "Performance|Security|Scalability|etc", "requirement": "<detail>"}}
    ],
    "user_stories": [
      {{
        "id": "US-001",
        "as_a": "<role>",
        "i_want": "<capability>",
        "so_that": "<benefit>",
        "acceptance_criteria": ["<criterion>"]
      }}
    ],
    "stakeholders": ["<stakeholder>"],
    "out_of_scope": ["<item>"],
    "assumptions": ["<assumption>"],
    "constraints": ["<constraint>"]
  }}
}}"""


# ─── Public API ──────────────────────────────────────────────────────────────

async def ba_process_initial(session: ProjectSession) -> dict:
    """Analyse the initial requirement. Returns raw BAResponse dict."""
    user_msg = (
        f"Analyse this software requirement and decide if you need clarification "
        f"to produce a complete BRD:\n\nREQUIREMENT:\n{session.original_requirement}"
        f"\n\nRound: 1 of {MAX_BA_ROUNDS}"
    )
    session.ba_messages = [{"role": "user", "content": user_msg}]

    # Use Haiku for initial triage — it's just categorising what we have
    raw = await call_claude(MODELS["ba_clarify"], _SYSTEM, session.ba_messages)
    session.ba_messages.append({"role": "assistant", "content": raw})
    return parse_json(raw)


async def ba_process_clarification(session: ProjectSession, answers: str) -> dict:
    """Feed user's answers back; decide whether more questions or BRD."""
    round_num = len(session.clarification_rounds) + 1
    final = round_num >= MAX_BA_ROUNDS

    user_msg = (
        f"User's answers:\n\n{answers}\n\n"
        f"Round: {round_num} of {MAX_BA_ROUNDS}"
        + (
            "\n\nFINAL ROUND — produce the complete BRD now using reasonable "
            "assumptions for anything still unclear."
            if final else ""
        )
    )
    session.ba_messages.append({"role": "user", "content": user_msg})

    # Switch to Sonnet once we have enough context to produce the BRD
    model = MODELS["ba_brd"] if final else MODELS["ba_clarify"]
    raw = await call_claude(model, _SYSTEM, session.ba_messages)
    session.ba_messages.append({"role": "assistant", "content": raw})
    return parse_json(raw)


async def ba_force_brd(session: ProjectSession) -> dict:
    """Force BRD output after max rounds (Sonnet for structured generation)."""
    force_msg = (
        "MAX ROUNDS REACHED. Produce the REQUIREMENTS_COMPLETE JSON BRD now. "
        "Document all assumptions clearly."
    )
    session.ba_messages.append({"role": "user", "content": force_msg})
    raw = await call_claude(MODELS["ba_brd"], _SYSTEM, session.ba_messages, max_tokens=8_000)
    result = parse_json(raw)
    if result.get("status") != "REQUIREMENTS_COMPLETE":
        raise RuntimeError("BA failed to produce BRD after maximum rounds")
    return result["brd"]
