"""
Session persistence via MongoDB (motor async driver).

Config via env vars:
  MONGODB_URI  — connection string (default: mongodb://localhost:27017)
  MONGODB_DB   — database name    (default: se_agents)
"""

from __future__ import annotations
import dataclasses
import os

import motor.motor_asyncio

from core.models import ClarificationRound, ProjectSession, SessionState

# ─── Connection (lazy init) ───────────────────────────────────────────────────

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None
_col = None


def _get_col():
    global _client, _col
    if _col is None:
        uri     = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB",  "se_agents")
        _client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        _col    = _client[db_name]["sessions"]
    return _col


# ─── Schema init ─────────────────────────────────────────────────────────────

async def init_db() -> None:
    await _get_col().create_index("chat_id", unique=True)


# ─── CRUD ────────────────────────────────────────────────────────────────────

async def save_session(session: ProjectSession) -> None:
    data = dataclasses.asdict(session)   # enums with str base serialize as strings
    await _get_col().update_one(
        {"chat_id": session.chat_id},
        {"$set": data},
        upsert=True,
    )


async def load_session(chat_id: int) -> ProjectSession | None:
    doc = await _get_col().find_one({"chat_id": chat_id}, {"_id": 0})
    return _from_dict(doc) if doc else None


async def delete_session(chat_id: int) -> None:
    await _get_col().delete_one({"chat_id": chat_id})


# ─── Deserialisation ─────────────────────────────────────────────────────────

def _from_dict(d: dict) -> ProjectSession:
    d = dict(d)
    d["state"] = SessionState(d["state"])
    d["clarification_rounds"] = [
        ClarificationRound(**r) for r in d.get("clarification_rounds", [])
    ]
    return ProjectSession(**d)
