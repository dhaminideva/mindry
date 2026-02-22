"""
tools/structurer.py
Converts raw transcript → StructuredThought via local Ollama (free).
"""
import structlog
from core.schemas import StructuredThought
from tools.ollama_client import chat, parse_json_response

log = structlog.get_logger()

SYSTEM_PROMPT = """You are a thought-structuring engine. Extract structured intent from messy spoken thoughts.

Return ONLY valid JSON — no explanation, no markdown, no extra text. Just the JSON object:
{
  "primary_goal": "the core thing the person wants to achieve",
  "constraints": ["list of limitations or requirements they mentioned"],
  "emotional_state": "calm|anxious|excited|confused|frustrated|motivated|neutral",
  "conflicts_detected": ["any contradictions in what they said"],
  "clarifying_questions_needed": ["questions needed only if truly unclear, else empty list"],
  "confidence_score": 0.85
}

confidence_score rules: 0.0–1.0. If the goal is reasonably clear, score 0.7+. Only go below 0.5 if truly ambiguous.
IMPORTANT: Return ONLY the raw JSON object. No markdown fences. No explanation."""


class ThoughtStructurerTool:
    async def run(self, transcript: str) -> StructuredThought:
        log.info("structurer_running", transcript_len=len(transcript))
        try:
            raw = await chat(SYSTEM_PROMPT, transcript)
            # Fix truncated JSON — llama3 sometimes cuts off the closing brace
            raw = raw.strip()
            if raw.count('{') > raw.count('}'):
                raw += '}'
            data = parse_json_response(raw)
            thought = StructuredThought(raw_transcript=transcript, **data)
            log.info("structurer_done", confidence=thought.confidence_score)
            return thought
        except Exception as e:
            log.error("structurer_error", error=str(e))
            return StructuredThought(
                raw_transcript=transcript,
                primary_goal="",
                confidence_score=0.1,
                clarifying_questions_needed=["Could you rephrase what you're trying to achieve?"],
            )
