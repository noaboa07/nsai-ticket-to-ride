from __future__ import annotations

from ttr_nsai.ai.base import AgentDecision, BaseAgent, CandidateDecision
from ttr_nsai.engine.models import GameState
from ttr_nsai.symbolic.reasoner import SymbolicReasoner


class SymbolicHeuristicAgent(BaseAgent):
    name = "symbolic"

    def __init__(self, reasoner: SymbolicReasoner) -> None:
        super().__init__()
        self.reasoner = reasoner

    def decide(self, state: GameState) -> AgentDecision:
        assessments = [self.reasoner.assess_action(state, action) for action in self.reasoner.legal_actions(state)]
        ranked = sorted(assessments, key=lambda assessment: assessment.base_score, reverse=True)
        best = ranked[0]
        candidates = [
            CandidateDecision(
                action=assessment.action,
                label=self.reasoner.action_label(state, assessment.action),
                total_score=assessment.base_score,
                heuristic_score=assessment.heuristic_score,
                symbolic_adjustment=assessment.symbolic_adjustment,
                explanation=assessment.explanation,
            )
            for assessment in ranked[:3]
        ]
        trace_lines = ["Decision trace:"]
        for index, candidate in enumerate(candidates, start=1):
            trace_lines.append(
                f"{index}. {candidate.label} | total={candidate.total_score:.2f} "
                f"(heuristic={candidate.heuristic_score:.2f}, symbolic={candidate.symbolic_adjustment:.2f})"
            )
        trace_lines.append(f"Chosen: {self.reasoner.action_label(state, best.action)}")
        trace_lines.append(f"Why: {best.explanation}")
        return AgentDecision(
            action=best.action,
            explanation=best.explanation,
            score=best.base_score,
            candidates=candidates,
            trace="\n".join(trace_lines),
        )
