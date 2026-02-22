"""
tools/contradiction.py
Detects conflicts in structured thought via local Ollama (free).
"""
import json
import structlog
from core.schemas import StructuredThought
from tools.ollama_client import chat, parse_json_response

log = structlog.get_logger()

SYSTEM_PROMPT = """You are a contradiction detector. Given goal and constraints, identify logical conflicts.

Return ONLY a JSON array of strings. Each string = one conflict found.
If no conflicts, return [].
Example: ["Wants passive income but unwilling to invest time upfront"]

IMPORTANT: Return ONLY the raw JSON array. No markdown. No explanation."""


class ConflictDetectorTool:
    async def run(self, thought: StructuredThought) -> list[str]:
        if thought.conflicts_detected:
            return thought.conflicts_detected
        try:
            payload = json.dumps({
                "primary_goal": thought.primary_goal,
                "constraints": thought.constraints,
                "emotional_state": thought.emotional_state,
            })
            raw = await chat(SYSTEM_PROMPT, payload)
            parsed = parse_json_response(raw)
            if isinstance(parsed, list):
                return parsed
            return parsed.get("conflicts", [])
        except Exception as e:
            log.error("conflict_detector_error", error=str(e))
            return []
