from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ttr_nsai.ai.base import AgentDecision, BaseAgent, CandidateDecision
from ttr_nsai.engine.models import Action, ActionType, CardColor, GameState
from ttr_nsai.symbolic.reasoner import SymbolicReasoner


@dataclass(frozen=True)
class FeatureVector:
    route_points: float
    route_length: float
    ticket_progress: float
    card_pressure: float
    destination_draw_value: float
    train_draw_value: float
    endgame_pressure: float
    block_value: float


class HybridNeuroSymbolicAgent(BaseAgent):
    name = "hybrid"

    def __init__(self, reasoner: SymbolicReasoner, weights: Dict[str, float] | None = None) -> None:
        super().__init__()
        self.reasoner = reasoner
        self.weights = weights or {
            "route_points": 1.5,
            "route_length": 0.7,
            "ticket_progress": 3.0,
            "card_pressure": -1.0,
            "destination_draw_value": 1.2,
            "train_draw_value": 1.0,
            "endgame_pressure": 1.5,
            "block_value": 1.4,
        }

    def decide(self, state: GameState) -> AgentDecision:
        legal_actions = self.reasoner.legal_actions(state)
        scored_actions: list[tuple[float, CandidateDecision]] = []
        for action in legal_actions:
            features = self.extract_features(state, action)
            heuristic_score = self.score_features(features)
            symbolic_bonus = self.reasoner.strategic_adjustment(state, action)
            assessment = self.reasoner.assess_action(state, action)
            total = heuristic_score + symbolic_bonus + 0.35 * assessment.heuristic_score
            explanation = (
                f"{assessment.explanation} Weighted model score={heuristic_score:.2f}, "
                f"symbolic adjustment={symbolic_bonus:.2f}."
            )
            candidate = CandidateDecision(
                action=action,
                label=self.reasoner.action_label(state, action),
                total_score=total,
                heuristic_score=heuristic_score + 0.35 * assessment.heuristic_score,
                symbolic_adjustment=symbolic_bonus,
                explanation=explanation,
            )
            scored_actions.append((total, candidate))

        ranked = [item[1] for item in sorted(scored_actions, key=lambda item: item[0], reverse=True)]
        best = ranked[0]
        trace_lines = ["Decision trace:"]
        for index, candidate in enumerate(ranked[:3], start=1):
            trace_lines.append(
                f"{index}. {candidate.label} | total={candidate.total_score:.2f} "
                f"(heuristic={candidate.heuristic_score:.2f}, symbolic={candidate.symbolic_adjustment:.2f})"
            )
            trace_lines.append(f"   {candidate.explanation}")
        trace_lines.append(f"Chosen: {best.label}")
        return AgentDecision(
            action=best.action,
            explanation=best.explanation,
            score=best.total_score,
            candidates=ranked[:3],
            trace="\n".join(trace_lines),
        )

    def extract_features(self, state: GameState, action: Action) -> FeatureVector:
        player = state.active_player()
        if action.action_type == ActionType.CLAIM_ROUTE and action.route_id:
            route = state.route_by_id(action.route_id)
            ticket_progress = self.reasoner.ticket_progress_delta(state, player, route)
            chosen_color = action.color or route.color or CardColor.RED
            card_gap = max(0, route.length - (player.hand.get(chosen_color, 0) + player.hand.get(CardColor.WILD, 0)))
            block_value = self.reasoner.blocking_value(state, player, route)
            endgame_pressure = 1.0 if player.trains_remaining <= 5 else 0.0
            return FeatureVector(
                route_points=route.points,
                route_length=route.length,
                ticket_progress=ticket_progress,
                card_pressure=float(card_gap),
                destination_draw_value=0.0,
                train_draw_value=0.0,
                endgame_pressure=endgame_pressure,
                block_value=block_value,
            )

        destination_value = 1.0 if action.action_type == ActionType.DRAW_DESTINATIONS and len(player.tickets) <= 2 else 0.0
        train_draw_value = 1.0 if action.action_type == ActionType.DRAW_TRAIN_CARDS else 0.0
        card_pressure = 0.0 if player.total_cards() < 8 else 1.0
        return FeatureVector(
            route_points=0.0,
            route_length=0.0,
            ticket_progress=0.0,
            card_pressure=card_pressure,
            destination_draw_value=destination_value,
            train_draw_value=train_draw_value,
            endgame_pressure=1.0 if player.trains_remaining <= 5 else 0.0,
            block_value=0.0,
        )

    def score_features(self, features: FeatureVector) -> float:
        return sum(getattr(features, name) * weight for name, weight in self.weights.items())
