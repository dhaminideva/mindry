"""
core/state_machine.py
Deterministic state machine for Mindry agent.
"""
from enum import Enum
from typing import Optional
import structlog

log = structlog.get_logger()


class State(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    EXTRACTING = "EXTRACTING"
    STRUCTURING = "STRUCTURING"
    VERIFYING = "VERIFYING"
    REFINING = "REFINING"
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"


# Valid transitions: {from_state: [allowed_to_states]}
TRANSITIONS: dict[State, list[State]] = {
    State.IDLE:        [State.LISTENING, State.EXTRACTING],
    State.LISTENING:   [State.EXTRACTING, State.INTERRUPTED],
    State.EXTRACTING:  [State.STRUCTURING, State.INTERRUPTED, State.REFINING],
    State.STRUCTURING: [State.VERIFYING, State.INTERRUPTED],
    State.VERIFYING:   [State.COMPLETED, State.REFINING, State.INTERRUPTED],
    State.REFINING:    [State.EXTRACTING, State.STRUCTURING, State.INTERRUPTED],
    State.COMPLETED:   [State.IDLE, State.LISTENING],
    State.INTERRUPTED: [State.EXTRACTING, State.IDLE],
}


class StateMachine:
    def __init__(self):
        self.state: State = State.IDLE
        self.previous_state: Optional[State] = None

    def transition(self, to: State) -> bool:
        allowed = TRANSITIONS.get(self.state, [])
        if to not in allowed:
            log.warning("invalid_transition", from_state=self.state, to_state=to)
            return False
        log.info("state_transition", from_state=self.state, to_state=to)
        self.previous_state = self.state
        self.state = to
        return True

    def interrupt(self):
        log.info("interrupt_triggered", current_state=self.state)
        self.previous_state = self.state
        self.state = State.INTERRUPTED

    def resume(self):
        self.transition(State.EXTRACTING)

    def reset(self):
        self.previous_state = self.state
        self.state = State.IDLE
