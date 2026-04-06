"""
Solution Architect Agent  (Opus — most complex reasoning task)

Input : BRD dict
Output: Architecture Document dict
"""

from __future__ import annotations
from config import MODELS
from core.claude import call_claude, parse_json

_SYSTEM = """You are a senior Solution Architect AI. Design robust, scalable architectures.

INPUT : BRD JSON
OUTPUT: Architecture Document JSON — respond with ONLY valid JSON, no prose.

Required structure:
{
  "system_overview": "<comprehensive overview>",
  "architecture_pattern": "<Microservices|Monolith|Event-Driven|etc>",
  "tech_stack": [
    {"layer": "<Frontend|Backend|Database|Cache|Queue|Infra|etc>",
     "technology": "<name>", "version": "<recommended>", "rationale": "<why>"}
  ],
  "components": [
    {"name": "<name>", "type": "<Service|Module|Gateway|etc>",
     "responsibility": "<what it does>",
     "interfaces": ["<exposed API/interface>"],
     "dependencies": ["<component names it depends on>"]}
  ],
  "data_flow": "<how data moves through the system>",
  "infrastructure": ["<infra requirement>"],
  "security_considerations": ["<security measure>"],
  "scalability_notes": "<how it scales>",
  "adrs": [
    {"id": "ADR-001", "title": "<decision>",
     "status": "PROPOSED|ACCEPTED|DEPRECATED",
     "context": "<why needed>", "decision": "<what was decided>",
     "consequences": ["<consequence>"]}
  ]
}"""


async def sa_generate(brd: dict) -> dict:
    msg = (
        "Design the architecture for this project based on the BRD:\n\n"
        + __import__("json").dumps(brd, indent=2)
    )
    raw = await call_claude(MODELS["sa"], _SYSTEM, [{"role": "user", "content": msg}])
    return parse_json(raw)
