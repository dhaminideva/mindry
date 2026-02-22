"""
guardrails/policy.py
Input safety checks before any LLM call.
"""
import structlog
from dataclasses import dataclass

log = structlog.get_logger()

# ── Customize these keyword lists to your needs ─────────────────────────────
BLOCKED_PATTERNS = [
    # Medical diagnosis
    ("diagnose", "I can't act as a medical diagnostic tool."),
    ("do i have", "I can't act as a medical diagnostic tool."),
    ("what disease", "I can't act as a medical diagnostic tool."),
    # Legal advice — use word boundaries to avoid false matches like "issue", "because"
    (" sue ", "I can't provide legal advice — please consult a lawyer."),
    ("i want to sue", "I can't provide legal advice — please consult a lawyer."),
    ("file a lawsuit", "I can't provide legal advice — please consult a lawyer."),
    ("is it legal to", "I can't provide legal advice — please consult a lawyer."),
    # Self-harm signals
    ("kill myself", "It sounds like you might be struggling. Please reach out to a crisis line: 988 (US)."),
    ("end my life", "It sounds like you might be struggling. Please reach out to a crisis line: 988 (US)."),
    ("want to die", "It sounds like you might be struggling. Please reach out to a crisis line: 988 (US)."),
]


@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""


class GuardrailsPolicy:
    def check_input(self, text: str) -> GuardResult:
        lower = text.lower()
        for pattern, reason in BLOCKED_PATTERNS:
            if pattern in lower:
                log.warning("guardrail_triggered", pattern=pattern)
                return GuardResult(allowed=False, reason=reason)
        return GuardResult(allowed=True)