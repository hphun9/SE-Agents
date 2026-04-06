"""
Backend Developer Agent  (Opus — complex code generation)

Input : BRD + Architecture + Tech Spec
Output: Backend Implementation Guide (project scaffold + key code)
"""

from __future__ import annotations
import json
from config import MODELS
from core.claude import call_claude, parse_json

_SYSTEM = """You are a senior Backend Developer AI. Generate practical, runnable backend implementation guides.

INPUT : BRD + Architecture + Technical Spec JSON
OUTPUT: Backend Implementation JSON — respond with ONLY valid JSON, no prose.

Required structure:
{
  "overview": "<implementation approach>",
  "tech_stack_used": ["<technology>"],
  "setup_guide": "<step-by-step setup and run instructions>",
  "project_structure": [
    {"path": "<directory/file>", "purpose": "<what it contains>"}
  ],
  "key_files": [
    {
      "path": "<relative/path/to/file>",
      "purpose": "<what this file does>",
      "code": "<actual implementation code>"
    }
  ],
  "database_setup": "<migration/schema setup instructions>",
  "api_implementation_notes": [
    {"endpoint": "<METHOD /path>",
     "notes": "<implementation details, gotchas, patterns to use>"}
  ],
  "environment_variables": ["<VAR_NAME=example_value>"],
  "deployment_notes": "<Docker/cloud deployment guide>",
  "next_steps": ["<what the dev should do next>"]
}

Guidelines:
- Provide REAL, runnable code in key_files (not pseudocode)
- Use the technologies from the architecture document
- Include authentication, error handling, and validation patterns
- Show at least: main entry point, routing, a model, a controller, and auth middleware"""


async def dev_backend_generate(
    brd: dict,
    architecture: dict,
    tech_spec: dict,
) -> dict:
    msg = (
        "Generate the backend implementation guide based on:\n\n"
        f"BRD:\n{json.dumps(brd, indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(architecture, indent=2)}\n\n"
        f"TECH SPEC:\n{json.dumps(tech_spec, indent=2)}"
    )
    raw = await call_claude(
        MODELS["dev_backend"], _SYSTEM,
        [{"role": "user", "content": msg}],
        max_tokens=16_000,
    )
    return parse_json(raw)
