"""
tests/test_core.py
Basic unit tests for Mindry core components.
Run: pytest tests/
"""
import pytest
from core.state_machine import StateMachine, State
from core.schemas import StructuredThought
from guardrails.policy import GuardrailsPolicy


# ── State Machine Tests ────────────────────────────────────────────────────

def test_initial_state():
    sm = StateMachine()
    assert sm.state == State.IDLE

def test_valid_transition():
    sm = StateMachine()
    result = sm.transition(State.EXTRACTING)
    assert result is True
    assert sm.state == State.EXTRACTING

def test_invalid_transition():
    sm = StateMachine()
    result = sm.transition(State.COMPLETED)  # Can't jump from IDLE to COMPLETED
    assert result is False
    assert sm.state == State.IDLE  # Unchanged

def test_interrupt_from_any_state():
    sm = StateMachine()
    sm.transition(State.EXTRACTING)
    sm.interrupt()
    assert sm.state == State.INTERRUPTED

def test_resume_after_interrupt():
    sm = StateMachine()
    sm.transition(State.EXTRACTING)
    sm.interrupt()
    sm.resume()
    assert sm.state == State.EXTRACTING

def test_full_happy_path():
    sm = StateMachine()
    sm.transition(State.EXTRACTING)
    sm.transition(State.STRUCTURING)
    sm.transition(State.VERIFYING)
    sm.transition(State.COMPLETED)
    assert sm.state == State.COMPLETED


# ── Schema Tests ──────────────────────────────────────────────────────────

def test_structured_thought_defaults():
    t = StructuredThought(raw_transcript="I want to build something")
    assert t.confidence_score == 0.0
    assert t.constraints == []
    assert t.emotional_state == "neutral"
    assert t.idea_id  # auto-generated

def test_structured_thought_full():
    t = StructuredThought(
        raw_transcript="test",
        primary_goal="Build a SaaS",
        constraints=["no funding", "solo founder"],
        emotional_state="excited",
        confidence_score=0.85,
    )
    assert t.primary_goal == "Build a SaaS"
    assert len(t.constraints) == 2
    assert t.confidence_score == 0.85


# ── Guardrails Tests ──────────────────────────────────────────────────────

def test_guardrails_allows_normal():
    g = GuardrailsPolicy()
    result = g.check_input("I want to start a business but I'm scared")
    assert result.allowed is True

def test_guardrails_blocks_medical():
    g = GuardrailsPolicy()
    result = g.check_input("can you diagnose my symptoms")
    assert result.allowed is False
    assert "medical" in result.reason.lower()

def test_guardrails_blocks_legal():
    g = GuardrailsPolicy()
    result = g.check_input("is it legal to resell tickets")
    assert result.allowed is False

def test_guardrails_blocks_self_harm():
    g = GuardrailsPolicy()
    result = g.check_input("I want to kill myself")
    assert result.allowed is False
    assert "988" in result.reason  # Crisis line should be in response
