"""
Project Manager Agent  (Sonnet — structured planning, moderate complexity)

Input : BRD + Architecture Document
Output: Project Plan dict
"""

from __future__ import annotations
import json
from config import MODELS
from core.claude import call_claude, parse_json

_SYSTEM = """You are a senior Project Manager AI with Agile expertise.

INPUT : BRD + Architecture Document JSON
OUTPUT: Project Plan JSON — respond with ONLY valid JSON, no prose.

Required structure:
{
  "project_name": "<name>",
  "duration_weeks": <total weeks>,
  "methodology": "<Scrum|Kanban|SAFe|etc>",
  "phases": [
    {"name": "<name>", "duration_weeks": <weeks>,
     "description": "<what happens>",
     "deliverables": ["<deliverable>"],
     "dependencies": ["<dependency>"]}
  ],
  "team_structure": [
    {"role": "<role>", "count": <number>,
     "responsibilities": ["<responsibility>"]}
  ],
  "milestones": [
    {"name": "<name>", "week": <week number>,
     "criteria": ["<success criterion>"]}
  ],
  "risks": [
    {"id": "R-001", "description": "<risk>",
     "probability": "LOW|MEDIUM|HIGH",
     "impact": "LOW|MEDIUM|HIGH",
     "mitigation": "<strategy>", "owner": "<role>"}
  ],
  "communication_plan": "<meetings, reporting cadence, tools>"
}"""


async def pm_generate(brd: dict, architecture: dict) -> dict:
    msg = (
        "Create a project plan based on:\n\n"
        f"BRD:\n{json.dumps(brd, indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(architecture, indent=2)}"
    )
    raw = await call_claude(MODELS["pm"], _SYSTEM, [{"role": "user", "content": msg}])
    return parse_json(raw)
