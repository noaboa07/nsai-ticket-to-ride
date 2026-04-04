from __future__ import annotations

import pytest

from ttr_nsai.engine.game import IllegalMoveError
from ttr_nsai.engine.models import Action, ActionType, CardColor

from tests.utils import clear_hands


def test_claim_route_requires_matching_cards(game, state) -> None:
    clear_hands(state)
    state.players[0].hand[CardColor.RED] = 1
    with pytest.raises(IllegalMoveError):
        game.apply_action(state, Action(ActionType.CLAIM_ROUTE, route_id="r1", color=CardColor.RED))


def test_gray_route_can_use_any_affordable_color(game, state, reasoner) -> None:
    clear_hands(state)
    state.players[0].hand[CardColor.BLUE] = 2
    legal_actions = reasoner.legal_actions(state)
    assert Action(ActionType.CLAIM_ROUTE, route_id="r6", color=CardColor.BLUE) in legal_actions


def test_colored_route_rejects_wrong_nonwild_color(game, state, reasoner) -> None:
    clear_hands(state)
    state.players[0].hand[CardColor.BLUE] = 2
    action = Action(ActionType.CLAIM_ROUTE, route_id="r1", color=CardColor.BLUE)
    assert not reasoner.is_legal(state, action)
    with pytest.raises(IllegalMoveError):
        game.apply_action(state, action)


def test_gray_route_rejects_mixed_nonwild_cards(game, state, reasoner) -> None:
    clear_hands(state)
    state.players[0].hand[CardColor.RED] = 1
    state.players[0].hand[CardColor.BLUE] = 1
    assert Action(ActionType.CLAIM_ROUTE, route_id="r6", color=CardColor.RED) not in reasoner.legal_actions(state)
    assert Action(ActionType.CLAIM_ROUTE, route_id="r6", color=CardColor.BLUE) not in reasoner.legal_actions(state)


def test_wild_cards_substitute_for_colored_route(game, state, reasoner) -> None:
    clear_hands(state)
    state.players[0].hand[CardColor.RED] = 1
    state.players[0].hand[CardColor.WILD] = 1
    action = Action(ActionType.CLAIM_ROUTE, route_id="r1", color=CardColor.RED)
    assert reasoner.is_legal(state, action)
    game.apply_action(state, action)
    assert state.players[0].hand[CardColor.RED] == 0
    assert state.players[0].hand[CardColor.WILD] == 0


def test_wild_cards_substitute_for_gray_route_with_selected_color(game, state, reasoner) -> None:
    clear_hands(state)
    state.players[0].hand[CardColor.BLUE] = 1
    state.players[0].hand[CardColor.WILD] = 1
    action = Action(ActionType.CLAIM_ROUTE, route_id="r6", color=CardColor.BLUE)
    assert reasoner.is_legal(state, action)
    game.apply_action(state, action)
    assert "r6" in state.players[0].claimed_route_ids


def test_gray_route_requires_explicit_color_selection(game, state, reasoner) -> None:
    clear_hands(state)
    state.players[0].hand[CardColor.BLUE] = 2
    action = Action(ActionType.CLAIM_ROUTE, route_id="r6", color=None)
    assert not reasoner.is_legal(state, action)
    with pytest.raises(IllegalMoveError):
        game.apply_action(state, action)


def test_claimed_route_becomes_illegal(game, state, reasoner) -> None:
    clear_hands(state)
    state.players[0].hand[CardColor.RED] = 2
    game.apply_action(state, Action(ActionType.CLAIM_ROUTE, route_id="r1", color=CardColor.RED))
    legal_actions = reasoner.legal_actions(state, state.players[1])
    assert Action(ActionType.CLAIM_ROUTE, route_id="r1", color=CardColor.RED) not in legal_actions
