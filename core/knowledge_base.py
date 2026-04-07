"""
Self-learning Knowledge Base

Every time the /fix flow runs and QA confirms tests pass, the error +
root cause + solution is saved to MongoDB. The next time a similar error
appears — in any project — the fixer gets the past solution as context,
so it never starts from zero on a problem it has already solved.

Schema (collection: knowledge_base):
  error_description  — original error text
  error_type         — auth | database | network | config | logic | type | syntax | other
  keywords           — extracted by Haiku for text-index search
  tech_stack         — ["python", "fastapi", "jwt", ...]
  root_cause         — what actually caused the error
  solution_summary   — what was done to fix it
  files_pattern      — relative paths that were changed (for reference)
  fix_worked         — True if QA passed after applying the fix
  confidence         — 0.0–1.0, increases each time the solution is reused
  use_count          — how many times this solution was applied
  created_at / last_used
"""

from __future__ import annotations
import os
import uuid
from datetime import datetime
from typing import Optional

import motor.motor_asyncio

from config import MODELS
from core.claude import call_claude, parse_json

# ─── Lazy connection ──────────────────────────────────────────────────────────

_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_col = None


def _get_col():
    global _client, _col
    if _col is None:
        uri     = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "se_agents")
        _client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        _col    = _client[db_name]["knowledge_base"]
    return _col


# ─── Schema init ─────────────────────────────────────────────────────────────

async def init_kb() -> None:
    """Create text index for full-text search across all knowledge fields."""
    col = _get_col()
    await col.create_index(
        [
            ("error_description", "text"),
            ("root_cause",        "text"),
            ("solution_summary",  "text"),
            ("keywords",          "text"),
            ("tech_stack",        "text"),
        ],
        name="knowledge_text_idx",
        weights={
            "keywords":    10,
            "error_type":   8,
            "root_cause":   5,
            "solution_summary": 4,
            "error_description": 3,
            "tech_stack":   2,
        },
    )
    await col.create_index("error_type")
    await col.create_index([("confidence", -1)])
    await col.create_index([("use_count", -1)])


# ─── Metadata extraction (Haiku — cheap) ─────────────────────────────────────

_EXTRACT_SYSTEM = (
    "Extract structured metadata from a software error description. "
    "Respond with ONLY valid JSON, no prose.\n\n"
    "Return: {\n"
    '  "keywords":   ["specific", "error", "terms"],\n'
    '  "error_type": "auth|database|network|config|logic|type|syntax|permission|timeout|memory|other",\n'
    '  "tech_stack": ["detected", "technologies"],\n'
    '  "severity":   "critical|high|medium|low"\n'
    "}"
)


async def _extract_meta(error: str, tech_hint: list[str] | None = None) -> dict:
    """Use Haiku to extract keywords and categorise the error cheaply."""
    content = f"Error:\n{error}"
    if tech_hint:
        content += f"\n\nDetected technologies: {', '.join(tech_hint)}"
    raw = await call_claude(
        MODELS["fixer_triage"], _EXTRACT_SYSTEM,
        [{"role": "user", "content": content}],
        max_tokens=300,
    )
    try:
        return parse_json(raw)
    except Exception:
        return {"keywords": [], "error_type": "other", "tech_stack": [], "severity": "medium"}


# ─── Search ───────────────────────────────────────────────────────────────────

async def search_similar(
    error_description: str,
    tech_stack: list[str] | None = None,
    limit: int = 3,
) -> list[dict]:
    """
    Find the most relevant past solutions for a given error.
    Returns up to `limit` entries, ranked by relevance score.
    Only returns solutions where fix_worked=True.
    """
    col = _get_col()
    meta = await _extract_meta(error_description, tech_stack)
    keywords = meta.get("keywords", [])
    detected_tech = list(set(meta.get("tech_stack", []) + (tech_stack or [])))

    search_text = " ".join(keywords[:12]) or error_description[:300]

    pipeline = [
        {"$match": {
            "$text": {"$search": search_text},
            "fix_worked": True,
        }},
        {"$addFields": {
            "text_score":  {"$meta": "textScore"},
            "tech_overlap": {
                "$size": {
                    "$ifNull": [
                        {"$setIntersection": ["$tech_stack", detected_tech]},
                        [],
                    ]
                }
            },
        }},
        # Composite score: text relevance + tech overlap + confidence + usage
        {"$addFields": {
            "score": {
                "$add": [
                    {"$multiply": ["$text_score",    10.0]},
                    {"$multiply": ["$tech_overlap",   5.0]},
                    {"$multiply": ["$confidence",     3.0]},
                    {"$multiply": ["$use_count",      0.5]},
                ]
            }
        }},
        {"$sort": {"score": -1}},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "error_type":       1,
            "root_cause":       1,
            "solution_summary": 1,
            "tech_stack":       1,
            "confidence":       1,
            "use_count":        1,
            "score":            1,
        }},
    ]

    try:
        return await col.aggregate(pipeline).to_list(limit)
    except Exception:
        # Fallback: plain text search without scoring
        try:
            cursor = col.find(
                {"$text": {"$search": search_text}, "fix_worked": True},
                {"_id": 0, "error_type": 1, "root_cause": 1,
                 "solution_summary": 1, "tech_stack": 1, "confidence": 1},
            ).limit(limit)
            return await cursor.to_list(limit)
        except Exception:
            return []


async def search_for_user(query: str, limit: int = 5) -> list[dict]:
    """Text search for the /kb search command (includes failed attempts)."""
    col = _get_col()
    try:
        cursor = col.find(
            {"$text": {"$search": query}},
            {
                "_id": 0,
                "error_description": 1, "error_type": 1,
                "root_cause": 1, "solution_summary": 1,
                "tech_stack": 1, "fix_worked": 1,
                "confidence": 1, "use_count": 1,
            },
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        return await cursor.to_list(limit)
    except Exception:
        return []


# ─── Write ────────────────────────────────────────────────────────────────────

async def save_solution(
    error_description: str,
    analysis: str,
    solution_summary: str,
    files_changed: list[dict],
    tech_stack: list[str],
    fix_worked: bool,
) -> str:
    """
    Persist an error + solution to the knowledge base.

    If a nearly identical entry already exists the confidence score is raised
    and use_count is incremented instead of creating a duplicate.

    Returns the entry_id (new or existing).
    """
    col = _get_col()
    meta = await _extract_meta(error_description, tech_stack)

    combined_tech = list(set(meta.get("tech_stack", []) + tech_stack))
    keywords_text = " ".join(meta.get("keywords", [])[:10])

    # Dedup: look for a very similar successful entry of the same type
    existing = None
    if keywords_text and fix_worked:
        try:
            existing = await col.find_one({
                "$text": {"$search": keywords_text},
                "error_type": meta.get("error_type", "other"),
                "fix_worked": True,
            })
        except Exception:
            pass

    if existing:
        new_conf = min(1.0, existing.get("confidence", 0.5) + 0.1)
        await col.update_one(
            {"_id": existing["_id"]},
            {
                "$set":  {"confidence": round(new_conf, 2),
                          "last_used": datetime.utcnow().isoformat()},
                "$inc":  {"use_count": 1},
            },
        )
        return existing.get("entry_id", str(existing["_id"]))

    # New entry
    entry_id = str(uuid.uuid4())
    await col.insert_one({
        "entry_id":          entry_id,
        "error_description": error_description[:1000],
        "error_type":        meta.get("error_type", "other"),
        "keywords":          meta.get("keywords", []),
        "tech_stack":        combined_tech,
        "severity":          meta.get("severity", "medium"),
        "root_cause":        analysis[:2000],
        "solution_summary":  solution_summary[:1000],
        "files_pattern":     [f["path"] for f in files_changed],
        "fix_worked":        fix_worked,
        "confidence":        0.7 if fix_worked else 0.2,
        "use_count":         1,
        "created_at":        datetime.utcnow().isoformat(),
        "last_used":         datetime.utcnow().isoformat(),
    })
    return entry_id


# ─── Stats ────────────────────────────────────────────────────────────────────

async def get_stats() -> dict:
    col = _get_col()
    total      = await col.count_documents({})
    successful = await col.count_documents({"fix_worked": True})

    top_types_cur = col.aggregate([
        {"$group": {"_id": "$error_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 6},
    ])
    top_tech_cur = col.aggregate([
        {"$unwind": {"path": "$tech_stack", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": "$tech_stack", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 6},
    ])

    top_types = await top_types_cur.to_list(6)
    top_techs = await top_tech_cur.to_list(6)

    return {
        "total":        total,
        "successful":   successful,
        "success_rate": round(successful / total * 100, 1) if total else 0,
        "top_types":    [{"type": t["_id"], "count": t["count"]} for t in top_types if t["_id"]],
        "top_techs":    [{"tech": t["_id"], "count": t["count"]} for t in top_techs if t["_id"]],
    }
