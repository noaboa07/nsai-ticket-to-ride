from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ttr_nsai.engine.game import AgentProtocol
from ttr_nsai.engine.models import Action, GameState


@dataclass
class CandidateDecision:
    action: Action
    label: str
    total_score: float
    heuristic_score: float
    symbolic_adjustment: float
    explanation: str


@dataclass
class AgentDecision:
    action: Action
    explanation: str
    score: float
    candidates: list[CandidateDecision] = field(default_factory=list)
    trace: str = ""


class BaseAgent(AgentProtocol):
    name: str = "base"

    def __init__(self) -> None:
        self.last_decision: Optional[AgentDecision] = None

    def choose_action(self, state: GameState) -> Action:
        decision = self.decide(state)
        self.last_decision = decision
        return decision.action

    def decide(self, state: GameState) -> AgentDecision:
        raise NotImplementedError
