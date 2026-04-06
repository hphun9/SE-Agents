"""
Tech Lead Agent  (Opus — detailed technical reasoning)

Input : BRD + Architecture + Project Plan
Output: Technical Specification dict
"""

from __future__ import annotations
import json
from config import MODELS
from core.claude import call_claude, parse_json

_SYSTEM = """You are a senior Tech Lead AI. Produce comprehensive technical specifications.

INPUT : BRD + Architecture + Project Plan JSON
OUTPUT: Technical Specification JSON — respond with ONLY valid JSON, no prose.

Required structure:
{
  "overview": "<technical implementation overview>",
  "coding_standards": ["<standard>"],
  "development_workflow": "<git branching, PR process, review requirements>",
  "api_design": [
    {"method": "GET|POST|PUT|PATCH|DELETE",
     "path": "/api/v1/resource",
     "description": "<purpose>",
     "auth_required": true,
     "request_schema": {"field": "type"},
     "response_schema": {"field": "type"}}
  ],
  "data_models": [
    {"name": "<ModelName>",
     "description": "<what it represents>",
     "fields": [
       {"name": "<field>", "type": "<string|int|bool|uuid|datetime|etc>",
        "required": true, "description": "<purpose>"}
     ],
     "relationships": ["<relationship>"],
     "indexes": ["<field>"]
    }
  ],
  "technical_dependencies": [
    {"name": "<package>", "version": "<version>",
     "purpose": "<why>", "license": "<license>"}
  ],
  "sprint_plan": [
    {"sprint": 1, "goal": "<goal>",
     "user_stories": ["US-001"], "story_points": <points>}
  ],
  "definition_of_done": ["<criterion>"],
  "testing_strategy": "<unit/integration/e2e approach and coverage targets>"
}"""


async def tech_lead_generate(brd: dict, architecture: dict, project_plan: dict) -> dict:
    msg = (
        "Write the Technical Specification based on:\n\n"
        f"BRD:\n{json.dumps(brd, indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(architecture, indent=2)}\n\n"
        f"PROJECT PLAN:\n{json.dumps(project_plan, indent=2)}"
    )
    raw = await call_claude(MODELS["tech_lead"], _SYSTEM, [{"role": "user", "content": msg}])
    return parse_json(raw)
