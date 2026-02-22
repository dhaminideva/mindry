"""
core/orchestrator.py
Main agent orchestration loop.
Plan → Act → Verify → Recover.
"""
import time
import asyncio
import structlog
from core.state_machine import StateMachine, State
from core.schemas import StructuredThought, Roadmap, AgentResponse
from tools.structurer import ThoughtStructurerTool
from tools.contradiction import ConflictDetectorTool
from tools.roadmap import RoadmapGeneratorTool
from memory.store import MemoryStore
from guardrails.policy import GuardrailsPolicy
import os

log = structlog.get_logger()
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
OLLAMA_MODEL = os.getenv("LLM_MODEL", "llama3.2")


class MindryOrchestrator:
    def __init__(self):
        self.sm = StateMachine()
        self.memory = MemoryStore()
        self.structurer = ThoughtStructurerTool()
        self.conflict_detector = ConflictDetectorTool()
        self.roadmap_generator = RoadmapGeneratorTool()
        self.guardrails = GuardrailsPolicy()
        self._interrupted = False
        self._metrics = {
            "total_requests": 0,
            "latencies_ms": [],
            "interrupt_count": 0,
            "failed_verifications": 0,
            "schema_failures": 0,
        }

    async def init(self):
        await self.memory.init()

    def interrupt(self):
        """Call this when user speaks mid-response."""
        self._interrupted = True
        self.sm.interrupt()
        self._metrics["interrupt_count"] += 1
        log.info("orchestrator_interrupted")

    def _check_interrupt(self):
        if self._interrupted:
            raise asyncio.CancelledError("User interrupted")

    async def process(self, transcript: str) -> AgentResponse:
        self._interrupted = False
        self._metrics["total_requests"] += 1
        start = time.monotonic()
        # Reset state machine so each request starts fresh
        self.sm.reset()

        try:
            # ── PLAN: Extract structure ──────────────────────────────────
            self.sm.transition(State.EXTRACTING)
            self._check_interrupt()

            # Guardrails check BEFORE LLM call
            guard_result = self.guardrails.check_input(transcript)
            if not guard_result.allowed:
                        self.sm.reset()
                        return AgentResponse(
                            state=self.sm.state,
                            message=guard_result.reason,
                            clarifying_questions=[
                                "Would you like to rephrase and focus on the decision or life situation instead?"
                            ],
                        )

            thought: StructuredThought = await self.structurer.run(transcript)
            self._check_interrupt()

            # ── ACT: Structure + detect conflicts ────────────────────────
            self.sm.transition(State.STRUCTURING)
            conflicts = await self.conflict_detector.run(thought)
            thought.conflicts_detected = conflicts
            self._check_interrupt()

            # ── VERIFY ───────────────────────────────────────────────────
            self.sm.transition(State.VERIFYING)
            verify_result = self._verify(thought)

            if not verify_result["ok"]:
                self._metrics["failed_verifications"] += 1
                self.sm.transition(State.REFINING)
                elapsed = int((time.monotonic() - start) * 1000)
                self._metrics["latencies_ms"].append(elapsed)
                await self.memory.add_recording(thought.idea_id, transcript, thought)
                return AgentResponse(
                                    state=self.sm.state,
                                    thought=thought,
                                    message="I need a bit more clarity before I can build your plan.",
                                    clarifying_questions=thought.clarifying_questions_needed,
                                    conflicts=conflicts,
                                    metrics=self._get_metrics(elapsed),
                                )

            # ── PERSIST + GENERATE ROADMAP ───────────────────────────────
            # Always store the recording; save structured thought if confident enough
            # ── PERSIST + GENERATE ROADMAP ───────────────────────────────
            # Always save the recording regardless of confidence or verification
            await self.memory.add_recording(thought.idea_id, transcript, thought)
            if thought.confidence_score >= CONFIDENCE_THRESHOLD:
                await self.memory.save(thought)

            roadmap: Roadmap = await self.roadmap_generator.run(thought)
            self._check_interrupt()

            self.sm.transition(State.COMPLETED)
            elapsed = int((time.monotonic() - start) * 1000)
            self._metrics["latencies_ms"].append(elapsed)

            return AgentResponse(
                state=self.sm.state,
                thought=thought,
                roadmap=roadmap,
                message="Here's your structured plan.",
                conflicts=conflicts,
                metrics=self._get_metrics(elapsed),
            )

        except asyncio.CancelledError:
            elapsed = int((time.monotonic() - start) * 1000)
            self._metrics["latencies_ms"].append(elapsed)
            self.sm.state = State.INTERRUPTED
            return AgentResponse(
                state=self.sm.state,
                message="Got it — interrupted. Send your next thought whenever you're ready.",
                metrics=self._get_metrics(elapsed),
            )
        except Exception as e:
            log.error("orchestrator_error", error=str(e))
            self.sm.reset()
            return AgentResponse(
                state=self.sm.state,
                message=f"Something went wrong: {str(e)}",
            )

    def _verify(self, thought: StructuredThought) -> dict:
        issues = []
        if not thought.primary_goal:
            issues.append("No primary goal detected.")
        if thought.confidence_score < 0.3:
            issues.append("Confidence too low.")
        # Only block if confidence is low AND questions exist — not questions alone
        if thought.clarifying_questions_needed and thought.confidence_score < CONFIDENCE_THRESHOLD:
            issues.append("Clarification needed.")
        return {"ok": len(issues) == 0, "issues": issues}

    def _get_metrics(self, latest_ms: int) -> dict:
        lats = self._metrics["latencies_ms"]
        avg = int(sum(lats) / len(lats)) if lats else 0
        sorted_lats = sorted(lats)
        p95_idx = int(len(sorted_lats) * 0.95) - 1
        p95 = sorted_lats[max(0, p95_idx)] if sorted_lats else 0
        return {
            "avg_latency_ms": avg,
            "p95_latency_ms": p95,
            "latest_latency_ms": latest_ms,
            "total_requests": self._metrics["total_requests"],
            "interrupt_count": self._metrics["interrupt_count"],
            "failed_verifications": self._metrics["failed_verifications"],
        }
