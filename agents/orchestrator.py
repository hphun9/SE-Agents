"""
Orchestrator v2

Adapter-agnostic pipeline state machine.
Receives IncomingMessage from any chat adapter and sends OutgoingMessage back.
Supports interactive mode (existing flow) and autonomous/queue mode.
"""
from __future__ import annotations
import asyncio
import dataclasses
import json
import logging
import os
import uuid
from collections import deque
from typing import Optional

from adapters.base import ChatAdapter, IncomingMessage, OutgoingMessage
from core.models import (
    AgentMessage, AgentRole, MessageType,
    ClarificationRound, ProjectSession, SessionState,
    QueuedProject,
)
from core.storage import save_session as _db_save, load_session as _db_load, delete_session as _db_delete
from core.formatter import (
    fmt_brd, fmt_architecture, fmt_project_plan,
    fmt_tech_spec, fmt_backend_impl, fmt_frontend_impl, fmt_qa_plan,
)
from agents.ba import ba_process_initial, ba_process_clarification
from agents.sa import sa_generate
from agents.pm import pm_generate
from agents.tech_lead import tech_lead_generate
from agents.dev_backend import dev_backend_generate
from agents.dev_frontend import dev_frontend_generate
from agents.qa import qa_generate
from agents.fixer import analyze_and_fix
from agents.qa_runner import run_tests
from agents.consult import consult_agent, resolve_role, list_roles
from agents.secretary import secretary_dispatch, team_roster
from core.knowledge_base import search_similar, save_solution, get_stats, search_for_user
from config import MAX_BA_ROUNDS
from workspace.writer import WorkspaceWriter
from workspace.git_integration import GitIntegration

log = logging.getLogger(__name__)

# ─── In-memory session store ─────────────────────────────────────────────────
_sessions: dict[str, ProjectSession] = {}   # key = chat_id (str)

# ─── MarkdownV2 escape helper ────────────────────────────────────────────────
import re as _re
def _esc(t: str) -> str:
    return _re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(t))

class Orchestrator:
    def __init__(self):
        self._adapters: dict[str, ChatAdapter] = {}
        self._queue: deque[QueuedProject] = deque()
        self._queue_running = False
        self._autonomous = False
        self._default_prefs: dict = {}
        self._workspace = WorkspaceWriter(os.getenv("PROJECTS_DIR", "/tmp/projects"))

    # ─── Adapter registry ────────────────────────────────────────────────────

    def register_adapter(self, adapter: ChatAdapter) -> None:
        self._adapters[adapter.platform_name] = adapter

    def _adapter_for(self, platform: str) -> Optional[ChatAdapter]:
        return self._adapters.get(platform)

    # ─── Session helpers ─────────────────────────────────────────────────────

    async def _get_session(self, chat_id: str) -> Optional[ProjectSession]:
        if chat_id in _sessions:
            return _sessions[chat_id]
        s = await _db_load(int(chat_id) if chat_id.isdigit() else 0)
        if s:
            _sessions[chat_id] = s
        return s

    async def _new_session(self, chat_id: str, requirement: str) -> ProjectSession:
        s = ProjectSession(
            project_id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            chat_id=int(chat_id) if chat_id.isdigit() else hash(chat_id),
            state=SessionState.BA_CLARIFYING,
            original_requirement=requirement,
        )
        _sessions[chat_id] = s
        await _db_save(s)
        return s

    async def _clear_session(self, chat_id: str) -> None:
        _sessions.pop(chat_id, None)
        if chat_id.isdigit():
            await _db_delete(int(chat_id))

    async def _persist(self, session: ProjectSession) -> None:
        session.touch()
        await _db_save(session)

    # ─── Send helpers ─────────────────────────────────────────────────────────

    async def _send(self, platform: str, chat_id: str, text: str) -> None:
        adapter = self._adapter_for(platform)
        if adapter:
            await adapter.send(OutgoingMessage(chat_id=chat_id, text=text))

    async def _send_photo(self, platform: str, chat_id: str, photo: bytes, caption: str = "") -> None:
        adapter = self._adapter_for(platform)
        if adapter:
            await adapter.send(OutgoingMessage(
                chat_id=chat_id, text="", photo_bytes=photo, photo_caption=caption,
            ))

    async def _send_approval(self, platform: str, chat_id: str, project_id: str) -> None:
        adapter = self._adapter_for(platform)
        if not adapter:
            return
        await adapter.send(OutgoingMessage(
            chat_id=chat_id,
            text=(
                "📋 *Planning complete\\!*\n\n"
                "The team has produced:\n"
                "• ✅ Business Requirements Document\n"
                "• 🏗️ Architecture Document\n"
                "• 📅 Project Plan\n"
                "• ⚙️ Technical Specification\n\n"
                "Ready to hand off to the dev team?"
            ),
            inline_buttons=[[
                {"text": "✅ Approve — Start Dev Team", "callback_data": f"approve:{project_id}"},
                {"text": "📝 Request Changes",          "callback_data": f"changes:{project_id}"},
            ]],
        ))

    # ─── Main message entry point ─────────────────────────────────────────────

    async def handle_message(self, msg: IncomingMessage) -> None:
        """Route any incoming message from any adapter."""
        cid = msg.chat_id
        plt = msg.platform
        text = msg.text.strip()

        # ── Callback (button tap) ──
        if msg.callback_data:
            asyncio.create_task(self._handle_callback(plt, cid, msg.callback_data))
            return

        # ── Commands ──
        if text.startswith("/start"):
            await self._cmd_start(plt, cid)
        elif text.startswith("/new"):
            await self._cmd_new(plt, cid)
        elif text.startswith("/status"):
            await self._cmd_status(plt, cid)
        elif text.startswith("/help"):
            await self._cmd_help(plt, cid)
        elif text.startswith("/ask "):
            asyncio.create_task(self._cmd_ask(plt, cid, text[5:].strip()))
        elif text.lower().startswith("/s ") or text.lower() == "/s":
            asyncio.create_task(self._cmd_secretary(plt, cid, text.split(None, 1)[1].strip() if " " in text else ""))
        elif text.startswith("/fix "):
            asyncio.create_task(self._cmd_fix(plt, cid, text[5:].strip()))
        elif text.startswith("/queue"):
            asyncio.create_task(self._cmd_queue(plt, cid, text))
        elif text.startswith("/auto"):
            await self._cmd_auto(plt, cid, text)
        elif text.startswith("/overnight "):
            asyncio.create_task(self._cmd_overnight(plt, cid, text[11:].strip()))
        elif text.startswith("/kb"):
            asyncio.create_task(self._cmd_kb(plt, cid, text))
        elif text.startswith("/"):
            await self._send(plt, cid, f"Unknown command\\. Send /help for usage\\.")
        else:
            # ── Plain text → pipeline input ──
            asyncio.create_task(self._handle_text(plt, cid, text))

    # ─── Command handlers ─────────────────────────────────────────────────────

    async def _cmd_start(self, plt: str, cid: str) -> None:
        await self._send(plt, cid,
            "👋 *Welcome to SE\\-Agents v1\\.0\\.0\\!*\n\n"
            "I'm your AI software development team\\. Send your project requirement to begin\\.\n\n"
            "Or send /help to see all commands\\."
        )

    async def _cmd_new(self, plt: str, cid: str) -> None:
        await self._clear_session(cid)
        await self._send(plt, cid, "🆕 Session cleared\\. Send a requirement to start\\.")

    async def _cmd_status(self, plt: str, cid: str) -> None:
        session = await self._get_session(cid)
        if not session:
            await self._send(plt, cid, "📭 No active project\\. Send a requirement to start\\.")
            return
        labels = {
            SessionState.BA_CLARIFYING:        "🔍 BA is gathering requirements",
            SessionState.SA_PROCESSING:        "🏗️ SA is designing architecture",
            SessionState.PM_PROCESSING:        "📅 PM is creating project plan",
            SessionState.TECH_LEAD_PROCESSING: "⚙️ Tech Lead is writing spec",
            SessionState.AWAITING_APPROVAL:    "🔔 Awaiting your approval",
            SessionState.FEEDBACK_PENDING:     "📝 Awaiting your change feedback",
            SessionState.DEV_PROCESSING:       "💻 Dev team is implementing",
            SessionState.QA_PROCESSING:        "🧪 QA is writing test plan",
            SessionState.COMPLETE:             "✅ Pipeline complete",
        }
        label = _esc(labels.get(session.state, session.state))
        queue_info = f"\n*Queue:* {len(self._queue)} project\\(s\\) waiting" if self._queue else ""
        auto_info = "\n*Mode:* 🤖 Autonomous" if self._autonomous else ""
        await self._send(plt, cid,
            f"📊 *Project Status*\n\n"
            f"*ID:* `{_esc(session.project_id[:8])}`\n"
            f"*State:* {label}\n"
            f"*BA rounds:* {len(session.clarification_rounds)}\n"
            f"*Started:* {_esc(session.created_at[:10])}"
            f"{queue_info}{auto_info}"
        )

    async def _cmd_help(self, plt: str, cid: str) -> None:
        await self._send(plt, cid,
            "📖 *Commands*\n\n"
            "*(any text)* — start a new project\n"
            "/s \\<message\\> — 🤖 secretary: chat naturally, auto\\-routes to the right agent\n"
            "/ask \\<role\\> \\<question\\> — consult a specific agent directly\n"
            "/fix \\<path\\> \\<error\\> — dev fixes bug \\+ QA screenshot\n"
            "/new — clear current session\n"
            "/status — pipeline status\n"
            "/queue \\<requirement\\> — queue a project\n"
            "/queue list — show queue\n"
            "/queue clear — clear queue\n"
            "/auto on|off — toggle autonomous mode\n"
            "/overnight \\<requirement\\> — queue with auto\\-approve\n"
            "/kb stats — knowledge base statistics\n"
            "/kb search \\<query\\> — search past solutions\n"
            "/help — this message\n\n"
            f"*Roles for /ask:*\n{list_roles()}"
        )

    async def _cmd_ask(self, plt: str, cid: str, args: str) -> None:
        parts = args.split(None, 1)
        if len(parts) < 2:
            await self._send(plt, cid, "Usage: `/ask <role> <question>`")
            return
        role_key = resolve_role(parts[0])
        if not role_key:
            await self._send(plt, cid, f"Unknown role: `{_esc(parts[0])}`\n\n{list_roles()}")
            return
        session = await self._get_session(cid)
        await self._send(plt, cid, f"⏳ Consulting {_esc(parts[0])}\\.\\.\\.")
        try:
            response = await consult_agent(role_key, parts[1], session)
            await self._send(plt, cid, response)
        except Exception as exc:
            log.exception("consult_agent error")
            await self._send(plt, cid, f"❌ Error: {_esc(str(exc))}")

    async def _cmd_secretary(self, plt: str, cid: str, message: str) -> None:
        """
        Natural-language dispatcher — chat freely and the secretary
        automatically routes to the right specialist.
        """
        if not message:
            await self._send(plt, cid,
                "👋 *Hi\\! I'm your Secretary\\.* Just tell me what you need in plain language "
                "and I'll connect you to the right team member\\.\n\n"
                f"*The team:*\n{team_roster()}\n\n"
                "Example: `/s how should I design my auth service?`"
            )
            return

        await self._send(plt, cid, "🤖 *Secretary is thinking\\.\\.\\.*")
        session = await self._get_session(cid)
        try:
            result = await secretary_dispatch(message, session)
        except Exception as exc:
            log.exception("secretary error")
            await self._send(plt, cid, f"❌ Secretary error: {_esc(str(exc))}")
            return

        if result["routed_to"] == "secretary":
            # Direct answer — no routing needed
            header = "🤖 *Secretary*"
        else:
            # Routed to a specialist — show who answered
            header = (
                f"{result['emoji']} *{_esc(result['role_name'])}* "
                f"\\(via Secretary\\)"
            )

        await self._send(plt, cid, header)
        await self._send(plt, cid, result["response"])

    async def _cmd_fix(self, plt: str, cid: str, args: str) -> None:
        parts = args.split(None, 1)
        if len(parts) < 2:
            await self._send(plt, cid,
                "Usage: `/fix <project_path> <error description>`\n"
                "Example: `/fix /projects/myapp Fix 401 on POST /api/auth`"
            )
            return
        project_path, error_desc = parts[0], parts[1]
        await self._send(plt, cid, f"🔍 *Dev agent is analysing* `{_esc(project_path)}`\\.\\.\\.")

        # ── Step 0: Search knowledge base for past solutions ──────────────────
        kb_context = ""
        try:
            past = await search_similar(error_desc, limit=3)
            if past:
                lines = [
                    f"[{i+1}] error_type: {s.get('error_type','?')} | "
                    f"confidence: {round(s.get('confidence', 0) * 100)}% | "
                    f"used {s.get('use_count', 1)}x\n"
                    f"    Root cause:  {s.get('root_cause','')[:200]}\n"
                    f"    Solution:    {s.get('solution_summary','')[:200]}"
                    for i, s in enumerate(past)
                ]
                kb_context = (
                    "KNOWLEDGE BASE — Similar past solutions (use as reference, adapt to this project):\n"
                    + "\n".join(lines)
                )
                await self._send(plt, cid,
                    f"🧠 *Found {len(past)} similar past solution\\(s\\) in KB — injecting as context\\.*"
                )
        except Exception:
            log.warning("KB search failed — continuing without context", exc_info=True)

        # ── Step 1: Run the fixer ─────────────────────────────────────────────
        try:
            fix = await analyze_and_fix(project_path, error_desc, kb_context=kb_context)
        except Exception as exc:
            log.exception("fixer error")
            await self._send(plt, cid, f"❌ Fixer error: {_esc(str(exc))}")
            return

        changed = "\n".join(
            f"  • `{_esc(f['path'])}` \\({_esc(f['action'])}\\)"
            for f in fix["files_changed"]
        ) or "  _no files changed_"
        await self._send(plt, cid,
            f"🔧 *Fix applied*\n\n"
            f"*Analysis:* {_esc(fix['analysis'])}\n\n"
            f"*Files changed:*\n{changed}\n\n"
            f"*Summary:* {_esc(fix['diff_summary'])}\n\n"
            f"🧪 Running tests\\.\\.\\."
        )

        # ── Step 2: QA ────────────────────────────────────────────────────────
        result = None
        try:
            result = await run_tests(fix["project_path"], fix["test_command"])
        except Exception as exc:
            log.exception("qa_runner error")
            await self._send(plt, cid, f"❌ QA error: {_esc(str(exc))}")

        fix_worked = result["passed"] if result else False
        status = "✅ All tests passed" if fix_worked else "❌ Tests failed"

        if result:
            await self._send_photo(plt, cid, result["screenshot"],
                f"{status}\nCommand: {fix['test_command'] or 'n/a'}"
            )

        # ── Step 3: Save to knowledge base ────────────────────────────────────
        try:
            # Detect tech stack from file extensions of changed files
            ext_map = {
                ".py": "python", ".js": "javascript", ".ts": "typescript",
                ".jsx": "react", ".tsx": "react", ".go": "go", ".rs": "rust",
                ".java": "java", ".rb": "ruby", ".php": "php", ".cs": "csharp",
            }
            tech_stack: list[str] = []
            for f in fix["files_changed"]:
                ext = "." + f["path"].rsplit(".", 1)[-1].lower() if "." in f["path"] else ""
                tech = ext_map.get(ext)
                if tech and tech not in tech_stack:
                    tech_stack.append(tech)

            entry_id = await save_solution(
                error_description=error_desc,
                analysis=fix["analysis"],
                solution_summary=fix["diff_summary"],
                files_changed=fix["files_changed"],
                tech_stack=tech_stack,
                fix_worked=fix_worked,
            )
            kb_label = "✅ saved to KB" if fix_worked else "📝 saved to KB (failed — for reference)"
            log.info("KB entry %s: %s", entry_id, kb_label)
        except Exception:
            log.warning("KB save failed", exc_info=True)

    async def _cmd_queue(self, plt: str, cid: str, text: str) -> None:
        if text.strip() == "/queue list":
            if not self._queue:
                await self._send(plt, cid, "📭 Queue is empty\\.")
            else:
                lines = [f"{i+1}\\. {_esc(p.requirement[:70])}\\.\\.\\." for i, p in enumerate(self._queue)]
                await self._send(plt, cid, "📋 *Queue:*\n" + "\n".join(lines))
            return
        if text.strip() == "/queue clear":
            self._queue.clear()
            await self._send(plt, cid, "🗑️ Queue cleared\\.")
            return
        requirement = text[7:].strip()  # strip "/queue "
        if not requirement:
            await self._send(plt, cid, "Usage: `/queue <requirement>`")
            return
        await self._enqueue(plt, cid, requirement, auto_approve=self._autonomous)

    async def _cmd_auto(self, plt: str, cid: str, text: str) -> None:
        if "on" in text:
            self._autonomous = True
            await self._send(plt, cid, "🤖 Autonomous mode *ON* — projects will auto\\-approve\\.")
        elif "off" in text:
            self._autonomous = False
            await self._send(plt, cid, "👤 Autonomous mode *OFF* — approval required\\.")
        else:
            status = "ON 🤖" if self._autonomous else "OFF 👤"
            await self._send(plt, cid, f"Autonomous mode is currently *{status}*\\.")

    async def _cmd_overnight(self, plt: str, cid: str, requirement: str) -> None:
        if not requirement:
            await self._send(plt, cid, "Usage: `/overnight <requirement>`")
            return
        await self._enqueue(plt, cid, requirement, auto_approve=True)

    async def _cmd_kb(self, plt: str, cid: str, text: str) -> None:
        """Handle /kb stats and /kb search <query>."""
        parts = text.strip().split(None, 2)   # ["/kb", subcommand?, query?]
        sub = parts[1].lower() if len(parts) > 1 else "stats"

        if sub == "stats":
            try:
                s = await get_stats()
                type_lines = "\n".join(
                    f"  • {t['type']}: {t['count']}" for t in s["top_types"]
                ) or "  _none yet_"
                tech_lines = "\n".join(
                    f"  • {t['tech']}: {t['count']}" for t in s["top_techs"]
                ) or "  _none yet_"
                await self._send(plt, cid,
                    f"🧠 *Knowledge Base Stats*\n\n"
                    f"*Total entries:* {s['total']}\n"
                    f"*Successful fixes:* {s['successful']}\n"
                    f"*Success rate:* {s['success_rate']}%\n\n"
                    f"*Top error types:*\n{type_lines}\n\n"
                    f"*Top tech stacks:*\n{tech_lines}"
                )
            except Exception as exc:
                await self._send(plt, cid, f"❌ KB error: {_esc(str(exc))}")

        elif sub == "search":
            query = parts[2].strip() if len(parts) > 2 else ""
            if not query:
                await self._send(plt, cid, "Usage: `/kb search <query>`")
                return
            try:
                results = await search_for_user(query, limit=5)
                if not results:
                    await self._send(plt, cid, "🔍 No matching solutions found in the knowledge base\\.")
                    return
                lines = []
                for i, r in enumerate(results, 1):
                    worked = "✅" if r.get("fix_worked") else "❌"
                    conf = round(r.get("confidence", 0) * 100)
                    lines.append(
                        f"*{i}\\. {worked} {_esc(r.get('error_type','?'))}* \\({conf}% confidence\\)\n"
                        f"_{_esc(r.get('error_description','')[:100])}_\n"
                        f"Root cause: {_esc(r.get('root_cause','')[:150])}\n"
                        f"Solution: {_esc(r.get('solution_summary','')[:150])}"
                    )
                await self._send(plt, cid,
                    f"🔍 *KB Search: {_esc(query[:50])}*\n\n" + "\n\n".join(lines)
                )
            except Exception as exc:
                await self._send(plt, cid, f"❌ KB search error: {_esc(str(exc))}")

        else:
            await self._send(plt, cid,
                "Usage:\n"
                "• `/kb stats` — knowledge base statistics\n"
                "• `/kb search <query>` — search past solutions"
            )

    # ─── Queue ────────────────────────────────────────────────────────────────

    async def _enqueue(self, plt: str, cid: str, requirement: str, auto_approve: bool = False) -> None:
        project = QueuedProject(
            chat_id=cid, platform=plt, requirement=requirement,
            auto_approve=auto_approve, preferences=self._default_prefs.copy(),
        )
        self._queue.append(project)
        auto_label = " \\(auto\\-approve\\)" if auto_approve else ""
        await self._send(plt, cid,
            f"📥 *Queued{auto_label}* \\(position {len(self._queue)}\\):\n_{_esc(requirement[:80])}_"
        )
        if not self._queue_running:
            asyncio.create_task(self._run_queue())

    async def _run_queue(self) -> None:
        self._queue_running = True
        results = []
        last_project = None
        while self._queue:
            project = self._queue.popleft()
            last_project = project
            await self._send(project.platform, project.chat_id,
                f"🚀 *Starting queued project:*\n_{_esc(project.requirement[:80])}_"
            )
            try:
                await self._clear_session(project.chat_id)
                session = await self._new_session(project.chat_id, project.requirement)
                if project.auto_approve:
                    # Inject preferences context for BA so it can skip clarification
                    if project.preferences:
                        session.ba_messages.append({"role": "user", "content":
                            f"User requirement: {project.requirement}\n"
                            f"Tech preferences: {json.dumps(project.preferences)}\n"
                            "Running in autonomous mode — produce BRD directly without asking clarifying questions."
                        })
                await self._run_pipeline(project.platform, project.chat_id, session, project.auto_approve)
                results.append({"requirement": project.requirement, "success": True})
            except Exception as exc:
                log.exception("Queue project failed")
                await self._send(project.platform, project.chat_id, f"❌ Project failed: {_esc(str(exc))}")
                results.append({"requirement": project.requirement, "success": False, "error": str(exc)})
        self._queue_running = False

        # Send summary if more than one project ran
        if len(results) > 1 and last_project:
            lines = [f"{'✅' if r['success'] else '❌'} {_esc(r['requirement'][:60])}" for r in results]
            done = sum(1 for r in results if r["success"])
            await self._send(last_project.platform, last_project.chat_id,
                f"🌅 *Queue complete — {done}/{len(results)} succeeded*\n\n" + "\n".join(lines)
            )

    # ─── Text / state routing ─────────────────────────────────────────────────

    async def _handle_text(self, plt: str, cid: str, text: str) -> None:
        session = await self._get_session(cid)
        if not session or session.state == SessionState.COMPLETE:
            if session:
                await self._clear_session(cid)
            await self._send(plt, cid,
                f"🚀 *Starting your project\\!*\n\n"
                f"Requirement:\n_{_esc(text)}_\n\nThe team is spinning up\\.\\.\\."
            )
            session = await self._new_session(cid, text)
            await self._run_pipeline(plt, cid, session, auto_approve=False)

        elif session.state == SessionState.BA_CLARIFYING:
            await self._handle_clarification(plt, cid, session, text)

        elif session.state == SessionState.FEEDBACK_PENDING:
            session.change_feedback = text
            await self._run_planning(plt, cid, session)

        else:
            await self._send(plt, cid,
                f"⏳ The team is still working\\. State: *{_esc(session.state)}*"
            )

    async def _handle_callback(self, plt: str, cid: str, data: str) -> None:
        session = await self._get_session(cid)
        if data.startswith("approve:"):
            if session and session.state == SessionState.AWAITING_APPROVAL:
                await self._send(plt, cid, "✅ *Approved\\! Handing off to the dev team\\.\\.\\.*")
                await self._run_dev(plt, cid, session)
        elif data.startswith("changes:"):
            if session:
                session.state = SessionState.FEEDBACK_PENDING
                await self._persist(session)
                await self._send(plt, cid,
                    "📝 *What would you like to change?*\n\n"
                    "Describe your feedback and SA, PM, and Tech Lead will revise the documents\\."
                )

    # ─── Pipeline stages ──────────────────────────────────────────────────────

    async def _run_pipeline(self, plt: str, cid: str, session: ProjectSession, auto_approve: bool) -> None:
        """BA phase then planning."""
        await self._send(plt, cid, "🔍 *BA is analysing your requirement\\.\\.\\.*")
        try:
            resp = await ba_process_initial(session)
            await self._handle_ba_resp(plt, cid, session, resp, auto_approve)
        except Exception as exc:
            log.exception("BA error")
            session.state = SessionState.COMPLETE
            await self._send(plt, cid, f"❌ BA error: {_esc(str(exc))}")

    async def _handle_clarification(self, plt: str, cid: str, session: ProjectSession, answers: str) -> None:
        if session.clarification_rounds:
            session.clarification_rounds[-1].answers = answers
        await self._persist(session)
        await self._send(plt, cid, "🤔 *BA is reviewing your answers\\.\\.\\.*")
        try:
            resp = await ba_process_clarification(session, answers)
            await self._handle_ba_resp(plt, cid, session, resp, False)
        except Exception as exc:
            log.exception("BA clarification error")
            session.state = SessionState.COMPLETE
            await self._send(plt, cid, f"❌ Error: {_esc(str(exc))}")

    async def _handle_ba_resp(self, plt: str, cid: str, session: ProjectSession, resp: dict, auto_approve: bool) -> None:
        if resp.get("status") == "NEEDS_CLARIFICATION" and not auto_approve:
            session.clarification_rounds.append(ClarificationRound(
                iteration=resp["iteration"], questions=resp["questions"],
            ))
            session.state = SessionState.BA_CLARIFYING
            await self._persist(session)
            from core.formatter import fmt_clarification
            for chunk in fmt_clarification(resp.get("analysis", ""), resp["questions"], resp["iteration"]):
                await self._send(plt, cid, chunk)
            return
        brd = resp.get("brd")
        if not brd:
            await self._send(plt, cid, "❌ BA returned no BRD\\.")
            return
        session.brd = brd
        await self._persist(session)
        for chunk in fmt_brd(brd):
            await self._send(plt, cid, chunk)
        await self._run_planning(plt, cid, session, auto_approve)

    async def _run_planning(self, plt: str, cid: str, session: ProjectSession, auto_approve: bool = False) -> None:
        brd = dict(session.brd)
        if session.change_feedback:
            brd["_change_feedback"] = session.change_feedback

        # SA
        try:
            session.state = SessionState.SA_PROCESSING
            await self._send(plt, cid, "🏗️ *Solution Architect is designing the architecture\\.\\.\\.*")
            arch = await sa_generate(brd)
            session.architecture = arch
            await self._persist(session)
            for chunk in fmt_architecture(arch):
                await self._send(plt, cid, chunk)
        except Exception as exc:
            log.exception("SA error"); await self._send(plt, cid, f"❌ SA error: {_esc(str(exc))}"); return

        # PM
        try:
            session.state = SessionState.PM_PROCESSING
            await self._send(plt, cid, "📅 *Project Manager is creating the plan\\.\\.\\.*")
            plan = await pm_generate(session.brd, arch)
            session.project_plan = plan
            await self._persist(session)
            for chunk in fmt_project_plan(plan):
                await self._send(plt, cid, chunk)
        except Exception as exc:
            log.exception("PM error"); await self._send(plt, cid, f"❌ PM error: {_esc(str(exc))}"); return

        # Tech Lead
        try:
            session.state = SessionState.TECH_LEAD_PROCESSING
            await self._send(plt, cid, "⚙️ *Tech Lead is writing the technical spec\\.\\.\\.*")
            spec = await tech_lead_generate(session.brd, arch, plan)
            session.tech_spec = spec
            await self._persist(session)
            for chunk in fmt_tech_spec(spec):
                await self._send(plt, cid, chunk)
        except Exception as exc:
            log.exception("TL error"); await self._send(plt, cid, f"❌ Tech Lead error: {_esc(str(exc))}"); return

        session.state = SessionState.AWAITING_APPROVAL
        session.change_feedback = None
        await self._persist(session)

        if auto_approve:
            await self._send(plt, cid, "🤖 *Autonomous mode — auto\\-approving and starting dev team\\.*")
            await self._run_dev(plt, cid, session)
        else:
            await self._send_approval(plt, cid, session.project_id)

    async def _run_dev(self, plt: str, cid: str, session: ProjectSession) -> None:
        session.state = SessionState.DEV_PROCESSING
        pdir = self._workspace.project_dir(session.project_id)
        await self._send(plt, cid, "🚀 *Dev team starting — Backend and Frontend in parallel\\.\\.\\.*")
        try:
            backend_task  = asyncio.create_task(dev_backend_generate(session.brd, session.architecture, session.tech_spec))
            frontend_task = asyncio.create_task(dev_frontend_generate(session.brd, session.architecture, session.tech_spec))
            backend_impl, frontend_impl = await asyncio.gather(backend_task, frontend_task)
        except Exception as exc:
            log.exception("Dev error"); await self._send(plt, cid, f"❌ Dev error: {_esc(str(exc))}"); return

        session.backend_impl  = backend_impl
        session.frontend_impl = frontend_impl
        await self._persist(session)

        for chunk in fmt_backend_impl(backend_impl):
            await self._send(plt, cid, chunk)
        for chunk in fmt_frontend_impl(frontend_impl):
            await self._send(plt, cid, chunk)

        # Write backend files to workspace
        import json as _json
        backend_text = _json.dumps(backend_impl)
        written = self._workspace.extract_and_write_code(pdir, backend_text)
        frontend_text = _json.dumps(frontend_impl)
        written += self._workspace.extract_and_write_code(pdir, frontend_text)
        if written:
            git = GitIntegration(pdir)
            await git.init_repo()
            await git.commit("dev", f"{len(written)} files written")

        # QA
        try:
            session.state = SessionState.QA_PROCESSING
            await self._send(plt, cid, "🧪 *QA Engineer is writing the test plan\\.\\.\\.*")
            qa = await qa_generate(session.brd, session.tech_spec, backend_impl, frontend_impl)
            session.qa_plan = qa
            await self._persist(session)
            for chunk in fmt_qa_plan(qa):
                await self._send(plt, cid, chunk)
        except Exception as exc:
            log.exception("QA error"); await self._send(plt, cid, f"❌ QA error: {_esc(str(exc))}"); return

        session.state = SessionState.COMPLETE
        await self._persist(session)
        self._workspace.write_manifest(pdir, dataclasses.asdict(session))
        await self._send(plt, cid,
            f"🎉 *All done\\!*\n\n"
            f"Your full project package is ready\\.\n"
            f"📁 Workspace: `{_esc(str(pdir))}`\n\n"
            f"Send a new requirement to start another project\\."
        )
