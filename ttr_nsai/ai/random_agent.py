from __future__ import annotations

import random
from typing import Optional

from ttr_nsai.ai.base import AgentDecision, BaseAgent, CandidateDecision
from ttr_nsai.engine.models import GameState
from ttr_nsai.symbolic.reasoner import SymbolicReasoner


class RandomAgent(BaseAgent):
    name = "random"

    def __init__(self, reasoner: SymbolicReasoner, seed: Optional[int] = None) -> None:
        super().__init__()
        self.reasoner = reasoner
        self.random = random.Random(seed)

    def decide(self, state: GameState) -> AgentDecision:
        legal_actions = self.reasoner.legal_actions(state)
        action = self.random.choice(legal_actions)
        candidate = CandidateDecision(
            action=action,
            label=self.reasoner.action_label(state, action),
            total_score=0.0,
            heuristic_score=0.0,
            symbolic_adjustment=0.0,
            explanation="Random baseline: selected uniformly from legal actions.",
        )
        return AgentDecision(
            action=action,
            explanation="Randomly selected a legal move.",
            score=0.0,
            candidates=[candidate],
            trace=f"Chosen: {candidate.label}\nReason: {candidate.explanation}",
        )
