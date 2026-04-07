"""
Fixer Agent

Flow:
  1. List all source files in the project
  2. Ask Claude (Haiku — cheap triage) which files are relevant to the error
  3. Read those files (capped at ~80 KB total)
  4. (Optional) Inject past solutions from the Knowledge Base as context
  5. Ask Claude (Opus) to generate a precise fix
  6. Write the changed files back to disk
  7. Return a fix summary + test command for QA runner
"""

from __future__ import annotations
import os
from pathlib import Path

from config import MODELS
from core.claude import call_claude, parse_json

# ─── Constants ───────────────────────────────────────────────────────────────

_MAX_TOTAL_BYTES = 80_000
_MAX_FILE_BYTES  = 20_000
_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "coverage",
}
_SKIP_EXTS = {
    ".pyc", ".pyo", ".lock", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".zip", ".tar", ".gz",
}

_TRIAGE_SYSTEM = (
    "You are a developer triaging a bug report. "
    "Given a file list and error description, return the paths of files "
    "most likely to contain the bug (max 12 files). "
    "Respond with ONLY valid JSON: {\"files\": [\"path\", ...]}"
)

_FIX_SYSTEM = """You are a senior developer AI. Analyse the bug and generate a precise fix.

Respond with ONLY valid JSON — no prose, no markdown fences.

{
  "analysis":        "<root cause explanation>",
  "files_to_change": [
    {
      "path":    "<relative/path/to/file>",
      "action":  "modify|create",
      "content": "<complete new file content>"
    }
  ],
  "test_command":  "<command to verify the fix, e.g. pytest tests/ -v>",
  "diff_summary":  "<brief human-readable summary of what was changed and why>"
}"""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _list_files(root: Path) -> list[str]:
    result = []
    for dirpath, dirs, filenames in os.walk(root):
        dirs[:] = [
            d for d in dirs
            if d not in _SKIP_DIRS and not d.startswith(".")
        ]
        for fname in filenames:
            if Path(fname).suffix.lower() in _SKIP_EXTS:
                continue
            rel = Path(dirpath).relative_to(root) / fname
            result.append(str(rel).replace("\\", "/"))
    return sorted(result)


async def _triage(file_list: list[str], error: str) -> list[str]:
    """Haiku triage: pick the relevant files cheaply."""
    raw = await call_claude(
        MODELS["fixer_triage"],
        _TRIAGE_SYSTEM,
        [{"role": "user", "content":
            f"Error:\n{error}\n\nFiles:\n" + "\n".join(file_list)}],
        max_tokens=500,
    )
    try:
        return parse_json(raw).get("files", file_list[:12])
    except Exception:
        return file_list[:12]


# ─── Public API ──────────────────────────────────────────────────────────────

async def analyze_and_fix(
    project_path: str,
    error_description: str,
    kb_context: str = "",
) -> dict:
    """
    Read the project, generate a fix with Opus, apply it to disk.

    Args:
        project_path:      Absolute path to the project directory.
        error_description: The error text supplied by the user.
        kb_context:        Pre-formatted past solutions from the Knowledge Base
                           (injected as additional context before the Opus call).

    Returns:
        {
            "analysis":      str,
            "files_changed": [{"path": str, "action": str}],
            "test_command":  str,
            "diff_summary":  str,
            "project_path":  str,
        }
    """
    root = Path(project_path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project path not found: {root}")

    all_files = _list_files(root)
    if not all_files:
        raise ValueError("No readable source files found.")

    # Step 1 — cheap triage (Haiku)
    relevant = await _triage(all_files, error_description)

    # Step 2 — read files up to byte budget
    file_contents: dict[str, str] = {}
    total = 0
    for rel in relevant:
        abs_p = root / rel
        if not abs_p.is_file():
            continue
        size = abs_p.stat().st_size
        if size > _MAX_FILE_BYTES or total + size > _MAX_TOTAL_BYTES:
            continue
        file_contents[rel] = abs_p.read_text(encoding="utf-8", errors="replace")
        total += size

    if not file_contents:
        raise ValueError("Relevant files are too large to process.")

    # Step 3 — Opus fix generation (with optional KB context)
    files_block = "\n\n".join(
        f"=== {p} ===\n{c}" for p, c in file_contents.items()
    )
    user_content = f"Error to fix:\n{error_description}\n\n"
    if kb_context:
        user_content += f"{kb_context}\n\n"
    user_content += f"Project files:\n{files_block}"

    messages = [{"role": "user", "content": user_content}]

    raw = await call_claude(MODELS["fixer"], _FIX_SYSTEM, messages)
    fix = parse_json(raw)

    # Step 4 — apply changes
    files_changed = []
    for f in fix.get("files_to_change", []):
        rel = f["path"].lstrip("/")
        abs_p = root / rel
        abs_p.parent.mkdir(parents=True, exist_ok=True)
        abs_p.write_text(f["content"], encoding="utf-8")
        files_changed.append({"path": rel, "action": f.get("action", "modify")})

    return {
        "analysis":      fix.get("analysis", ""),
        "files_changed": files_changed,
        "test_command":  fix.get("test_command", ""),
        "diff_summary":  fix.get("diff_summary", ""),
        "project_path":  str(root),
    }
