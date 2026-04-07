"""
Session persistence via SQLite.

Uses the stdlib sqlite3 (sync) — DB ops are fast enough that async
is not necessary here. Sessions are stored as JSON blobs keyed by chat_id.
"""

from __future__ import annotations
import dataclasses
import json
import sqlite3
from pathlib import Path

from core.models import ClarificationRound, ProjectSession, SessionState

DB_PATH = Path("sessions.db")


# ─── Schema ──────────────────────────────────────────────────────────────────

def init_db() -> None:
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                chat_id    INTEGER PRIMARY KEY,
                data       TEXT    NOT NULL,
                updated_at TEXT    NOT NULL
            )
        """)


# ─── CRUD ────────────────────────────────────────────────────────────────────

def save_session(session: ProjectSession) -> None:
    data = json.dumps(_to_dict(session))
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT OR REPLACE INTO sessions (chat_id, data, updated_at) VALUES (?, ?, ?)",
            (session.chat_id, data, session.updated_at),
        )


def load_session(chat_id: int) -> ProjectSession | None:
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            "SELECT data FROM sessions WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    return _from_dict(json.loads(row[0])) if row else None


def delete_session(chat_id: int) -> None:
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM sessions WHERE chat_id = ?", (chat_id,))


# ─── Serialisation ───────────────────────────────────────────────────────────

def _to_dict(session: ProjectSession) -> dict:
    # dataclasses.asdict recurses into nested dataclasses; enums with str
    # base serialize naturally through json.dumps
    return dataclasses.asdict(session)


def _from_dict(d: dict) -> ProjectSession:
    d = dict(d)
    d["state"] = SessionState(d["state"])
    d["clarification_rounds"] = [
        ClarificationRound(**r) for r in d.get("clarification_rounds", [])
    ]
    return ProjectSession(**d)
