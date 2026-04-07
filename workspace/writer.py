"""
Writes agent outputs to a real local project directory.
Extracts code blocks and writes them to the correct file paths.
"""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

_CODE_WITH_PATH = re.compile(r'```(\w+):([^\n]+)\n(.*?)```', re.DOTALL)
_FILE_COMMENT   = re.compile(r'<!--\s*FILE:\s*([^\n]+?)\s*-->\s*```\w*\n(.*?)```', re.DOTALL)

_DOC_NAMES = {
    "brd":           "01-business-requirements.md",
    "architecture":  "02-architecture.md",
    "project_plan":  "03-project-plan.md",
    "tech_spec":     "04-technical-specification.md",
    "backend_impl":  "05-backend-implementation.md",
    "frontend_impl": "06-frontend-implementation.md",
    "qa_plan":       "07-test-plan.md",
}

class WorkspaceWriter:
    def __init__(self, base_dir: str = "/tmp/projects"):
        self.base_dir = Path(base_dir)

    def project_dir(self, project_id: str, name: Optional[str] = None) -> Path:
        safe = re.sub(r"[^\w\-]", "_", name or project_id)[:50]
        d = self.base_dir / safe
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_document(self, pdir: Path, doc_type: str, content: str) -> Path:
        docs = pdir / "docs"
        docs.mkdir(exist_ok=True)
        fname = _DOC_NAMES.get(doc_type, f"{doc_type}.md")
        p = docs / fname
        p.write_text(content, encoding="utf-8")
        return p

    def extract_and_write_code(self, pdir: Path, agent_output: str) -> list[Path]:
        """Parse code blocks with file paths and write them to disk."""
        written: list[Path] = []
        seen: set[str] = set()

        def _write(rel: str, code: str) -> None:
            rel = rel.strip().lstrip("/")
            if rel in seen:
                return
            seen.add(rel)
            out = pdir / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(code.strip() + "\n", encoding="utf-8")
            written.append(out)

        for _, path, code in _CODE_WITH_PATH.findall(agent_output):
            _write(path, code)
        for path, code in _FILE_COMMENT.findall(agent_output):
            _write(path, code)

        return written

    def write_manifest(self, pdir: Path, session_data: dict) -> Path:
        p = pdir / "se-agents-manifest.json"
        p.write_text(json.dumps({
            "generated_at":    datetime.utcnow().isoformat(),
            "project_id":      session_data.get("project_id"),
            "state":           session_data.get("state"),
        }, indent=2), encoding="utf-8")
        return p
