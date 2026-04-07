"""Auto-commit project files after each agent stage."""
from __future__ import annotations
import asyncio
import logging
from pathlib import Path

log = logging.getLogger(__name__)

class GitIntegration:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    async def init_repo(self) -> None:
        if not (self.project_dir / ".git").exists():
            await self._run("git init")
            await self._run("git checkout -b main")

    async def commit(self, agent_name: str, summary: str) -> None:
        await self._run("git add -A")
        msg = f"[SE-Agents/{agent_name}] {summary}"
        result = await self._run(f'git commit -m "{msg}" --allow-empty')
        if result:
            log.info("Git commit: %s", msg)

    async def _run(self, cmd: str) -> str:
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=str(self.project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip()
