from __future__ import annotations

from ttr_nsai.engine.models import Action, ActionType, CardColor

from tests.utils import clear_hands


def test_claim_route_updates_score_and_trains(game, state) -> None:
    clear_hands(state)
    player = state.players[0]
    player.hand[CardColor.RED] = 2
    game.apply_action(state, Action(ActionType.CLAIM_ROUTE, route_id="r1", color=CardColor.RED))
    assert player.score == 2
    assert player.trains_remaining == 18
    assert "r1" in player.claimed_route_ids


def test_draw_train_cards_increases_hand_size(game, state) -> None:
    player = state.players[0]
    before = player.total_cards()
    game.apply_action(state, Action(ActionType.DRAW_TRAIN_CARDS))
    assert player.total_cards() == before + 2
