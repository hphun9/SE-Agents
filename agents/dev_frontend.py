"""
Frontend Developer Agent  (Sonnet — moderate complexity)

Input : BRD + Architecture + Tech Spec
Output: Frontend Implementation Guide (component scaffold + key code)
"""

from __future__ import annotations
import json
from config import MODELS
from core.claude import call_claude, parse_json

_SYSTEM = """You are a senior Frontend Developer AI. Generate practical frontend implementation guides.

INPUT : BRD + Architecture + Technical Spec JSON
OUTPUT: Frontend Implementation JSON — respond with ONLY valid JSON, no prose.

Required structure:
{
  "overview": "<implementation approach>",
  "framework_and_tools": ["<framework>", "<tool>"],
  "setup_guide": "<step-by-step setup and run instructions>",
  "project_structure": [
    {"path": "<directory/file>", "purpose": "<what it contains>"}
  ],
  "key_components": [
    {
      "name": "<ComponentName>",
      "purpose": "<what it renders/does>",
      "props": ["<propName: type>"],
      "code": "<actual component code>"
    }
  ],
  "state_management": "<approach, store structure, key actions>",
  "routing_structure": ["<route path — component>"],
  "api_integration": "<how frontend calls the backend API, auth headers, error handling>",
  "styling_approach": "<CSS framework/approach, theme config>",
  "environment_variables": ["<VITE_VAR_NAME=example>"],
  "deployment_notes": "<build and deploy instructions>",
  "next_steps": ["<what the dev should do next>"]
}

Guidelines:
- Provide REAL, runnable component code
- Use the frontend technology from the architecture document
- Show: App.tsx/main entry, routing setup, a feature component, an API hook, auth context
- Include loading and error states in components"""


async def dev_frontend_generate(
    brd: dict,
    architecture: dict,
    tech_spec: dict,
) -> dict:
    msg = (
        "Generate the frontend implementation guide based on:\n\n"
        f"BRD:\n{json.dumps(brd, indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(architecture, indent=2)}\n\n"
        f"TECH SPEC:\n{json.dumps(tech_spec, indent=2)}"
    )
    raw = await call_claude(
        MODELS["dev_frontend"], _SYSTEM,
        [{"role": "user", "content": msg}],
        max_tokens=12_000,
    )
    return parse_json(raw)
