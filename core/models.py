"""
All data models for SE-Agents.

Inter-agent communication uses AgentMessage[T] envelopes — JSON only,
no natural language between agents.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ─── Roles & Message Types ───────────────────────────────────────────────────

class AgentRole(str, Enum):
    ORCHESTRATOR  = "ORCHESTRATOR"
    BA            = "BA"
    SA            = "SA"
    PM            = "PM"
    TECH_LEAD     = "TECH_LEAD"
    DEV_BACKEND   = "DEV_BACKEND"
    DEV_FRONTEND  = "DEV_FRONTEND"
    QA            = "QA"
    USER          = "USER"


class MessageType(str, Enum):
    REQUIREMENT_INPUT        = "REQUIREMENT_INPUT"
    CLARIFICATION_REQUEST    = "CLARIFICATION_REQUEST"
    CLARIFICATION_RESPONSE   = "CLARIFICATION_RESPONSE"
    REQUIREMENTS_CONFIRMED   = "REQUIREMENTS_CONFIRMED"
    ARCHITECTURE_DOCUMENT    = "ARCHITECTURE_DOCUMENT"
    PROJECT_PLAN             = "PROJECT_PLAN"
    TECHNICAL_SPEC           = "TECHNICAL_SPEC"
    APPROVAL_REQUEST         = "APPROVAL_REQUEST"
    APPROVAL_GRANTED         = "APPROVAL_GRANTED"
    CHANGE_REQUESTED         = "CHANGE_REQUESTED"
    BACKEND_IMPL             = "BACKEND_IMPL"
    FRONTEND_IMPL            = "FRONTEND_IMPL"
    QA_PLAN                  = "QA_PLAN"
    PIPELINE_COMPLETE        = "PIPELINE_COMPLETE"


# ─── Message Envelope ─────────────────────────────────────────────────────────

@dataclass
class AgentMessage:
    """Structured envelope for all inter-agent communication. No natural language."""
    type: MessageType
    from_role: AgentRole
    to_role: AgentRole
    payload: dict[str, Any]
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if "timestamp" not in self.metadata:
            self.metadata["timestamp"] = datetime.utcnow().isoformat()
        if "version" not in self.metadata:
            self.metadata["version"] = "1.0"


# ─── Session State ───────────────────────────────────────────────────────────

class SessionState(str, Enum):
    IDLE                     = "IDLE"
    BA_CLARIFYING            = "BA_CLARIFYING"
    SA_PROCESSING            = "SA_PROCESSING"
    PM_PROCESSING            = "PM_PROCESSING"
    TECH_LEAD_PROCESSING     = "TECH_LEAD_PROCESSING"
    AWAITING_APPROVAL        = "AWAITING_APPROVAL"
    FEEDBACK_PENDING         = "FEEDBACK_PENDING"
    DEV_PROCESSING           = "DEV_PROCESSING"
    QA_PROCESSING            = "QA_PROCESSING"
    COMPLETE                 = "COMPLETE"


@dataclass
class ClarificationRound:
    iteration: int
    questions: list[str]
    answers: str | None = None


@dataclass
class ProjectSession:
    project_id: str
    session_id: str
    chat_id: int
    state: SessionState
    original_requirement: str
    # Multi-turn BA conversation kept for Claude context continuity
    ba_messages: list[dict[str, str]] = field(default_factory=list)
    clarification_rounds: list[ClarificationRound] = field(default_factory=list)
    change_feedback: str | None = None
    # Documents (raw dicts matching each agent's JSON output schema)
    brd: dict[str, Any] | None = None
    architecture: dict[str, Any] | None = None
    project_plan: dict[str, Any] | None = None
    tech_spec: dict[str, Any] | None = None
    backend_impl: dict[str, Any] | None = None
    frontend_impl: dict[str, Any] | None = None
    qa_plan: dict[str, Any] | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()


# ─── Queue & Autonomous mode ─────────────────────────────────────────────────

@dataclass
class QueuedProject:
    chat_id: str
    platform: str
    requirement: str
    auto_approve: bool = False
    preferences: dict[str, Any] = field(default_factory=dict)
    priority: int = 0


class QueueState(str, Enum):
    PENDING    = "PENDING"
    PROCESSING = "PROCESSING"
    DONE       = "DONE"
    FAILED     = "FAILED"
