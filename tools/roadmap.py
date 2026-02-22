"""
tools/roadmap.py
Generates action roadmap via local Ollama (free).
"""
import json
import structlog
from core.schemas import StructuredThought, Roadmap, RoadmapStep
from tools.ollama_client import chat, parse_json_response

log = structlog.get_logger()

SYSTEM_PROMPT = """You are an action planner. Convert a structured thought into a clear, actionable roadmap.

Return ONLY valid JSON — no markdown, no explanation:
{
  "summary": "one sentence summary of the plan",
  "steps": [
    {
      "step_number": 1,
      "action": "specific action to take",
      "rationale": "why this step matters",
      "time_estimate": "e.g. 30 mins, 1 week"
    }
  ]
}

Generate 3–5 steps. Be concrete and specific. No generic advice. No motivational filler.
IMPORTANT: Return ONLY the raw JSON object. No markdown fences."""


class RoadmapGeneratorTool:
    async def run(self, thought: StructuredThought) -> Roadmap:
        log.info("roadmap_generating", idea_id=thought.idea_id)
        try:
            payload = json.dumps({
                "primary_goal": thought.primary_goal,
                "constraints": thought.constraints,
                "conflicts": thought.conflicts_detected,
            })
            raw = await chat(SYSTEM_PROMPT, payload)
            data = parse_json_response(raw)
            steps = [RoadmapStep(**s) for s in data.get("steps", [])]
            return Roadmap(
                idea_id=thought.idea_id,
                summary=data.get("summary", ""),
                steps=steps,
            )
        except Exception as e:
            log.error("roadmap_error", error=str(e))
            return Roadmap(idea_id=thought.idea_id, summary="Could not generate roadmap.", steps=[])
