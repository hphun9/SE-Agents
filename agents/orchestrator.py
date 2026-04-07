"""
Orchestrator

Full pipeline state machine:
  USER → BA (clarify loop) → SA → PM → Tech Lead
       → [USER APPROVAL]
       → Backend Dev ┐ (parallel)
         Frontend Dev┘
       → QA
       → COMPLETE

All inter-agent messages use AgentMessage envelopes (structured JSON).
Natural language only in Telegram-facing callbacks.
"""

from __future__ import annotations
import asyncio
import json
import logging
import uuid
from typing import Callable, Awaitable

from core.models import (
    AgentMessage, AgentRole, MessageType,
    ClarificationRound, ProjectSession, SessionState,
)
from agents.ba import ba_process_initial, ba_process_clarification, ba_force_brd
from agents.sa import sa_generate
from agents.pm import pm_generate
from agents.tech_lead import tech_lead_generate
from agents.dev_backend import dev_backend_generate
from agents.dev_frontend import dev_frontend_generate
from agents.qa import qa_generate
from core.formatter import (
    fmt_brd, fmt_architecture, fmt_project_plan,
    fmt_tech_spec, fmt_backend_impl, fmt_frontend_impl, fmt_qa_plan,
)
from config import MAX_BA_ROUNDS
from core.storage import (
    save_session as _db_save,
    load_session as _db_load,
    delete_session as _db_delete,
)

log = logging.getLogger(__name__)

# Callback type aliases
ProgressCB  = Callable[[str], Awaitable[None]]
ClarifyCB   = Callable[[list[str], str, int], Awaitable[None]]
DocumentCB  = Callable[[str, list[str]], Awaitable[None]]
CompleteCB  = Callable[[], Awaitable[None]]
ApprovalCB  = Callable[[str], Awaitable[None]]
ErrorCB     = Callable[[str], Awaitable[None]]

# ─── In-memory session store (write-through to MongoDB) ──────────────────────
_sessions: dict[int, ProjectSession] = {}


async def get_session(chat_id: int) -> ProjectSession | None:
    if chat_id in _sessions:
        return _sessions[chat_id]
    # Restore from DB after server restart
    session = await _db_load(chat_id)
    if session:
        _sessions[chat_id] = session
    return session


async def create_session(chat_id: int, requirement: str) -> ProjectSession:
    s = ProjectSession(
        project_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        chat_id=chat_id,
        state=SessionState.BA_CLARIFYING,
        original_requirement=requirement,
    )
    _sessions[chat_id] = s
    await _db_save(s)
    return s


async def clear_session(chat_id: int) -> None:
    _sessions.pop(chat_id, None)
    await _db_delete(chat_id)


async def _persist(session: ProjectSession) -> None:
    """Touch + write-through to MongoDB."""
    session.touch()
    await _db_save(session)


# ─── Envelope helper ─────────────────────────────────────────────────────────

def _msg(
    type_: MessageType,
    from_: AgentRole,
    to: AgentRole,
    payload: dict,
    session: ProjectSession,
) -> AgentMessage:
    m = AgentMessage(
        type=type_, from_role=from_, to_role=to,
        payload=payload,
        metadata={
            "project_id": session.project_id,
            "session_id": session.session_id,
        },
    )
    log.debug("[%s→%s] %s", from_.value, to.value, json.dumps(m.metadata))
    return m


# ─── Entry points ─────────────────────────────────────────────────────────────

async def start_project(
    chat_id: int,
    requirement: str,
    on_progress: ProgressCB,
    on_clarify: ClarifyCB,
    on_document: DocumentCB,
    on_approval_needed: ApprovalCB,
    on_complete: CompleteCB,
    on_error: ErrorCB,
) -> None:
    session = await create_session(chat_id, requirement)
    _msg(MessageType.REQUIREMENT_INPUT, AgentRole.USER, AgentRole.BA,
         {"raw_requirement": requirement}, session)

    await on_progress("🔍 *BA is analysing your requirement\\.\\.\\.*")
    try:
        response = await ba_process_initial(session)
        await _handle_ba_response(
            response, session,
            on_progress, on_clarify, on_document,
            on_approval_needed, on_complete, on_error,
        )
    except Exception as exc:
        log.exception("BA initial error")
        session.state = SessionState.COMPLETE
        await on_error(str(exc))


async def handle_clarification_answer(
    chat_id: int,
    answers: str,
    on_progress: ProgressCB,
    on_clarify: ClarifyCB,
    on_document: DocumentCB,
    on_approval_needed: ApprovalCB,
    on_complete: CompleteCB,
    on_error: ErrorCB,
) -> None:
    session = await get_session(chat_id)
    if not session or session.state != SessionState.BA_CLARIFYING:
        await on_error("No active clarification session. Send a new requirement to start.")
        return

    if session.clarification_rounds:
        session.clarification_rounds[-1].answers = answers
    await _persist(session)

    _msg(MessageType.CLARIFICATION_RESPONSE, AgentRole.USER, AgentRole.BA,
         {"answers": answers}, session)

    await on_progress("🤔 *BA is reviewing your answers\\.\\.\\.*")
    try:
        response = await ba_process_clarification(session, answers)
        await _handle_ba_response(
            response, session,
            on_progress, on_clarify, on_document,
            on_approval_needed, on_complete, on_error,
        )
    except Exception as exc:
        log.exception("BA clarification error")
        session.state = SessionState.COMPLETE
        await on_error(str(exc))


async def handle_approval(
    chat_id: int,
    on_progress: ProgressCB,
    on_document: DocumentCB,
    on_complete: CompleteCB,
    on_error: ErrorCB,
) -> None:
    session = await get_session(chat_id)
    if not session or session.state != SessionState.AWAITING_APPROVAL:
        await on_error("Nothing pending approval.")
        return
    _msg(MessageType.APPROVAL_GRANTED, AgentRole.USER, AgentRole.ORCHESTRATOR,
         {}, session)
    await _run_dev_pipeline(session, on_progress, on_document, on_complete, on_error)


async def handle_change_request(chat_id: int) -> None:
    session = await get_session(chat_id)
    if session:
        session.state = SessionState.FEEDBACK_PENDING
        await _persist(session)


async def handle_change_feedback(
    chat_id: int,
    feedback: str,
    on_progress: ProgressCB,
    on_document: DocumentCB,
    on_approval_needed: ApprovalCB,
    on_complete: CompleteCB,
    on_error: ErrorCB,
) -> None:
    session = await get_session(chat_id)
    if not session or session.state != SessionState.FEEDBACK_PENDING:
        await on_error("No pending feedback session.")
        return
    session.change_feedback = feedback
    _msg(MessageType.CHANGE_REQUESTED, AgentRole.USER, AgentRole.ORCHESTRATOR,
         {"feedback": feedback}, session)
    await _run_planning_pipeline(session, on_progress, on_document, on_approval_needed, on_error)


# ─── Internal pipeline stages ────────────────────────────────────────────────

async def _handle_ba_response(
    response: dict,
    session: ProjectSession,
    on_progress: ProgressCB,
    on_clarify: ClarifyCB,
    on_document: DocumentCB,
    on_approval_needed: ApprovalCB,
    on_complete: CompleteCB,
    on_error: ErrorCB,
) -> None:
    if response.get("status") == "NEEDS_CLARIFICATION":
        session.clarification_rounds.append(ClarificationRound(
            iteration=response["iteration"],
            questions=response["questions"],
        ))
        session.state = SessionState.BA_CLARIFYING
        await _persist(session)
        _msg(MessageType.CLARIFICATION_REQUEST, AgentRole.BA, AgentRole.USER,
             response, session)
        await on_clarify(response["questions"], response.get("analysis", ""), response["iteration"])
        return

    brd = response.get("brd")
    if not brd:
        await on_error("BA returned REQUIREMENTS_COMPLETE but no BRD payload.")
        return

    session.brd = brd
    await _persist(session)
    _msg(MessageType.REQUIREMENTS_CONFIRMED, AgentRole.BA, AgentRole.ORCHESTRATOR,
         {"brd": brd}, session)

    await on_document("Business Requirements Document", fmt_brd(brd))
    await _run_planning_pipeline(session, on_progress, on_document, on_approval_needed, on_error)


async def _run_planning_pipeline(
    session: ProjectSession,
    on_progress: ProgressCB,
    on_document: DocumentCB,
    on_approval_needed: ApprovalCB,
    on_error: ErrorCB,
) -> None:
    assert session.brd is not None

    brd_with_note = dict(session.brd)
    if session.change_feedback:
        brd_with_note["_change_feedback"] = session.change_feedback

    # SA
    try:
        session.state = SessionState.SA_PROCESSING
        await on_progress("🏗️ *Solution Architect is designing the architecture\\.\\.\\.*")
        arch = await sa_generate(brd_with_note)
        session.architecture = arch
        await _persist(session)
        _msg(MessageType.ARCHITECTURE_DOCUMENT, AgentRole.SA, AgentRole.ORCHESTRATOR,
             arch, session)
        await on_document("Architecture Document", fmt_architecture(arch))
    except Exception as exc:
        log.exception("SA error")
        await on_error(f"SA error: {exc}")
        return

    # PM
    try:
        session.state = SessionState.PM_PROCESSING
        await on_progress("📅 *Project Manager is creating the plan\\.\\.\\.*")
        plan = await pm_generate(session.brd, arch)
        session.project_plan = plan
        await _persist(session)
        _msg(MessageType.PROJECT_PLAN, AgentRole.PM, AgentRole.ORCHESTRATOR,
             plan, session)
        await on_document("Project Plan", fmt_project_plan(plan))
    except Exception as exc:
        log.exception("PM error")
        await on_error(f"PM error: {exc}")
        return

    # Tech Lead
    try:
        session.state = SessionState.TECH_LEAD_PROCESSING
        await on_progress("⚙️ *Tech Lead is writing the technical spec\\.\\.\\.*")
        spec = await tech_lead_generate(session.brd, arch, plan)
        session.tech_spec = spec
        await _persist(session)
        _msg(MessageType.TECHNICAL_SPEC, AgentRole.TECH_LEAD, AgentRole.ORCHESTRATOR,
             spec, session)
        await on_document("Technical Specification", fmt_tech_spec(spec))
    except Exception as exc:
        log.exception("Tech Lead error")
        await on_error(f"Tech Lead error: {exc}")
        return

    session.state = SessionState.AWAITING_APPROVAL
    session.change_feedback = None
    await _persist(session)
    _msg(MessageType.APPROVAL_REQUEST, AgentRole.ORCHESTRATOR, AgentRole.USER,
         {"project_id": session.project_id}, session)
    await on_approval_needed(session.project_id)


async def _run_dev_pipeline(
    session: ProjectSession,
    on_progress: ProgressCB,
    on_document: DocumentCB,
    on_complete: CompleteCB,
    on_error: ErrorCB,
) -> None:
    assert session.brd and session.architecture and session.tech_spec

    session.state = SessionState.DEV_PROCESSING
    await on_progress(
        "🚀 *Dev team is starting\\! Backend and Frontend working in parallel\\.\\.\\.*"
    )

    try:
        backend_task  = asyncio.create_task(
            dev_backend_generate(session.brd, session.architecture, session.tech_spec)
        )
        frontend_task = asyncio.create_task(
            dev_frontend_generate(session.brd, session.architecture, session.tech_spec)
        )
        backend_impl, frontend_impl = await asyncio.gather(backend_task, frontend_task)
    except Exception as exc:
        log.exception("Dev parallel error")
        await on_error(f"Dev error: {exc}")
        return

    session.backend_impl  = backend_impl
    session.frontend_impl = frontend_impl
    await _persist(session)

    _msg(MessageType.BACKEND_IMPL,  AgentRole.DEV_BACKEND,  AgentRole.ORCHESTRATOR, backend_impl,  session)
    _msg(MessageType.FRONTEND_IMPL, AgentRole.DEV_FRONTEND, AgentRole.ORCHESTRATOR, frontend_impl, session)

    await on_document("Backend Implementation Guide",  fmt_backend_impl(backend_impl))
    await on_document("Frontend Implementation Guide", fmt_frontend_impl(frontend_impl))

    # QA
    try:
        session.state = SessionState.QA_PROCESSING
        await on_progress("🧪 *QA Engineer is writing the test plan\\.\\.\\.*")
        qa = await qa_generate(session.brd, session.tech_spec, backend_impl, frontend_impl)
        session.qa_plan = qa
        await _persist(session)
        _msg(MessageType.QA_PLAN, AgentRole.QA, AgentRole.ORCHESTRATOR, qa, session)
        await on_document("QA Plan", fmt_qa_plan(qa))
    except Exception as exc:
        log.exception("QA error")
        await on_error(f"QA error: {exc}")
        return

    session.state = SessionState.COMPLETE
    await _persist(session)
    _msg(MessageType.PIPELINE_COMPLETE, AgentRole.ORCHESTRATOR, AgentRole.USER, {}, session)
    await on_complete()
