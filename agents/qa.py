"""
QA Engineer Agent  (Sonnet — structured test planning)

Input : BRD + Tech Spec + Backend/Frontend impl summaries
Output: QA Plan dict
"""

from __future__ import annotations
import json
from config import MODELS
from core.claude import call_claude, parse_json

_SYSTEM = """You are a senior QA Engineer AI. Create comprehensive test plans.

INPUT : BRD + Tech Spec + Backend/Frontend implementation summaries
OUTPUT: QA Plan JSON — respond with ONLY valid JSON, no prose.

Required structure:
{
  "strategy_overview": "<overall testing approach>",
  "test_framework": "<framework stack, e.g. pytest + Playwright>",
  "test_suites": [
    {
      "name": "<suite name>",
      "type": "unit|integration|e2e|performance|security",
      "priority": "HIGH|MEDIUM|LOW",
      "cases": [
        {
          "id": "TC-001",
          "title": "<test name>",
          "preconditions": ["<setup needed>"],
          "steps": ["<step 1>", "<step 2>"],
          "expected_result": "<what should happen>",
          "tags": ["smoke", "regression", "etc"]
        }
      ]
    }
  ],
  "automation_setup": "<how to set up the test framework with config files>",
  "coverage_targets": {
    "unit": "<percentage>",
    "integration": "<percentage>",
    "e2e": "<critical paths covered>"
  },
  "ci_integration": "<GitHub Actions / CI pipeline test config>",
  "test_data_strategy": "<how test data is managed>",
  "key_test_files": [
    {"path": "<test file path>", "purpose": "<what it tests>", "code": "<example test code>"}
  ]
}"""


async def qa_generate(
    brd: dict,
    tech_spec: dict,
    backend_impl: dict,
    frontend_impl: dict,
) -> dict:
    # Summarise impl docs to save tokens — QA only needs structure, not full code
    be_summary = {
        "setup": backend_impl.get("setup_guide", ""),
        "api_notes": backend_impl.get("api_implementation_notes", []),
        "structure": [f["path"] for f in backend_impl.get("key_files", [])],
    }
    fe_summary = {
        "setup": frontend_impl.get("setup_guide", ""),
        "components": [c["name"] for c in frontend_impl.get("key_components", [])],
        "routing": frontend_impl.get("routing_structure", []),
    }

    msg = (
        "Create the QA Plan based on:\n\n"
        f"BRD:\n{json.dumps(brd, indent=2)}\n\n"
        f"TECH SPEC:\n{json.dumps(tech_spec, indent=2)}\n\n"
        f"BACKEND SUMMARY:\n{json.dumps(be_summary, indent=2)}\n\n"
        f"FRONTEND SUMMARY:\n{json.dumps(fe_summary, indent=2)}"
    )
    raw = await call_claude(
        MODELS["qa"], _SYSTEM,
        [{"role": "user", "content": msg}],
        max_tokens=12_000,
    )
    return parse_json(raw)
