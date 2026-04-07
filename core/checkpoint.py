"""Save/restore pipeline state for crash recovery and retry."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import motor.motor_asyncio

class CheckpointManager:
    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        self._checkpoints = db["checkpoints"]
        self._failed      = db["failed_projects"]

    async def save(self, session_id: str, stage: str, data: dict) -> None:
        await self._checkpoints.update_one(
            {"session_id": session_id},
            {"$set": {"stage": stage, "data": data, "updated_at": datetime.utcnow()}},
            upsert=True,
        )

    async def load(self, session_id: str) -> Optional[dict]:
        return await self._checkpoints.find_one({"session_id": session_id}, {"_id": 0})

    async def save_failed(self, project_data: dict, error: str) -> None:
        await self._failed.insert_one({
            "project": project_data,
            "error": error,
            "failed_at": datetime.utcnow(),
        })

    async def pop_failed(self) -> list[dict]:
        docs = await self._failed.find({}, {"_id": 0}).to_list(50)
        await self._failed.delete_many({})
        return docs
