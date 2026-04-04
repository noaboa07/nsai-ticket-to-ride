from __future__ import annotations

from ttr_nsai.engine.models import Action, ActionType, CardColor, DestinationTicket

from tests.utils import clear_hands


def test_endgame_triggers_and_finishes(game, state) -> None:
    clear_hands(state)
    state.players[0].trains_remaining = 2
    state.players[0].hand[CardColor.RED] = 2
    state.players[1].hand[CardColor.BLUE] = 3
    state.players[0].tickets = [DestinationTicket(ticket_id="x", city1="Alder", city2="Benton", points=4)]
    state.players[1].tickets = [DestinationTicket(ticket_id="y", city1="Dover", city2="Harbor", points=4)]
    game.apply_action(state, Action(ActionType.CLAIM_ROUTE, route_id="r1", color=CardColor.RED))
    assert state.last_round_triggered
    assert not state.game_over
    game.apply_action(state, Action(ActionType.CLAIM_ROUTE, route_id="r9", color=CardColor.BLUE))
    assert state.game_over
    assert state.winner in (0, 1)
