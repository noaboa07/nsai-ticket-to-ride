from __future__ import annotations

from ttr_nsai.ai.hybrid_agent import HybridNeuroSymbolicAgent
from ttr_nsai.ai.random_agent import RandomAgent
from ttr_nsai.ai.symbolic_agent import SymbolicHeuristicAgent
from ttr_nsai.engine.models import ActionType, CardColor, DestinationTicket

from tests.utils import clear_hands


def test_random_agent_returns_legal_action(state, reasoner) -> None:
    agent = RandomAgent(reasoner, seed=3)
    action = agent.choose_action(state)
    assert reasoner.is_legal(state, action)


def test_symbolic_agent_prefers_ticket_helping_route(game, state, reasoner) -> None:
    clear_hands(state)
    player = state.players[0]
    player.tickets = [DestinationTicket(ticket_id="x", city1="Alder", city2="Harbor", points=7)]
    player.hand[CardColor.GREEN] = 2
    player.hand[CardColor.BLUE] = 2
    player.hand[CardColor.BLACK] = 2
    agent = SymbolicHeuristicAgent(reasoner)
    action = agent.choose_action(state)
    assert action.action_type == ActionType.CLAIM_ROUTE


def test_hybrid_agent_scores_features(reasoner, state) -> None:
    agent = HybridNeuroSymbolicAgent(reasoner)
    action = agent.choose_action(state)
    assert reasoner.is_legal(state, action)
    assert agent.last_decision is not None
    assert isinstance(agent.last_decision.score, float)


def test_symbolic_reasoning_prefers_ticket_distance_reduction(state, reasoner) -> None:
    clear_hands(state)
    player = state.players[0]
    player.tickets = [DestinationTicket(ticket_id="x", city1="Alder", city2="Harbor", points=7)]
    route_helpful = state.route_by_id("r3")
    route_unhelpful = state.route_by_id("r20")
    assert reasoner.ticket_progress_delta(state, player, route_helpful) > 0
    assert reasoner.ticket_progress_delta(state, player, route_unhelpful) == 0


def test_hybrid_agent_produces_decision_trace(reasoner, state) -> None:
    agent = HybridNeuroSymbolicAgent(reasoner)
    agent.choose_action(state)
    assert agent.last_decision is not None
    assert "Decision trace:" in agent.last_decision.trace
