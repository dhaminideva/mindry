"""
core/schemas.py
Pydantic schemas for structured thought extraction.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class StructuredThought(BaseModel):
    idea_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    primary_goal: str = ""
    constraints: list[str] = []
    emotional_state: str = "neutral"
    conflicts_detected: list[str] = []
    clarifying_questions_needed: list[str] = []
    confidence_score: float = 0.0
    raw_transcript: str = ""
    date_created: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    refined_count: int = 0


class RoadmapStep(BaseModel):
    step_number: int
    action: str
    rationale: str
    time_estimate: str = "unknown"


class Roadmap(BaseModel):
    idea_id: str
    steps: list[RoadmapStep]
    summary: str


class AgentResponse(BaseModel):
    state: str
    thought: Optional[StructuredThought] = None
    roadmap: Optional[Roadmap] = None
    message: str = ""
    clarifying_questions: list[str] = []
    conflicts: list[str] = []
    metrics: dict = {}
