"""
memory/store.py
File-backed storage — persists across server restarts.
"""
import json
import os
import structlog
from datetime import datetime
from core.schemas import StructuredThought

log = structlog.get_logger()
MEMORY_FILE = os.getenv("MEMORY_FILE", "mindry_memory.json")


class MemoryStore:
    def __init__(self):
        self._store: dict[str, dict] = {}

    async def init(self):
        self._load()
        log.info("memory_store_ready", type="file-backed", file=MEMORY_FILE, loaded=len(self._store))

    def _load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    self._store = json.load(f)
            except Exception as e:
                log.error("memory_load_error", error=str(e))
                self._store = {}
    def get_conflict_history(self) -> list[dict]:
        """Return all conflicts across all entries, with timestamps, for longitudinal tracking."""
        history = []
        for item in self._store.values():
            for conflict in item.get("conflicts_detected", []):
                history.append({
                    "idea_id": item["idea_id"],
                    "conflict": conflict,
                    "primary_goal": item["primary_goal"],
                    "date": item["date_created"],
                    "emotional_state": item["emotional_state"],
                })
        return sorted(history, key=lambda x: x["date"])
    def _save(self):
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._store, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error("memory_save_error", error=str(e))

    async def add_recording(self, idea_id: str, transcript: str, thought: StructuredThought):
        if idea_id not in self._store:
            self._store[idea_id] = {
                **thought.model_dump(),
                "recordings": [],
            }
        self._store[idea_id]["recordings"].append({
            "transcript": transcript,
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": thought.confidence_score,
        })
        self._save()
        log.info("recording_saved", idea_id=idea_id,
                 total_recordings=len(self._store[idea_id]["recordings"]))

    async def save(self, thought: StructuredThought):
        existing = self._store.get(thought.idea_id, {})
        self._store[thought.idea_id] = {
            **thought.model_dump(),
            "recordings": existing.get("recordings", []),
        }
        self._save()
        log.info("thought_saved", idea_id=thought.idea_id, total=len(self._store))

    async def get_all(self) -> list[dict]:
        return sorted(
            self._store.values(),
            key=lambda t: t["date_created"],
            reverse=True,
        )

    async def get_by_id(self, idea_id: str) -> dict | None:
        return self._store.get(idea_id)

    async def delete(self, idea_id: str):
        self._store.pop(idea_id, None)
        self._save()

    def count(self) -> int:
        return len(self._store)