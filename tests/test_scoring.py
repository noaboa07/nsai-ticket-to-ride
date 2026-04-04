from __future__ import annotations

from ttr_nsai.engine.models import DestinationTicket
from ttr_nsai.engine.scoring import is_ticket_completed, longest_route_length, score_tickets

from tests.utils import clear_hands


def test_ticket_completion_detects_connection(game, state) -> None:
    clear_hands(state)
    player = state.players[0]
    player.claimed_route_ids.extend(["r3", "r10", "r12", "r14"])
    ticket = DestinationTicket(ticket_id="x", city1="Alder", city2="Harbor", points=7)
    assert is_ticket_completed(player, ticket, game.routes_by_id)


def test_score_tickets_penalizes_unfinished(game, state) -> None:
    player = state.players[0]
    player.tickets = [DestinationTicket(ticket_id="x", city1="Alder", city2="Harbor", points=7)]
    ticket_score, completed = score_tickets(player, game.routes_by_id)
    assert ticket_score == -7
    assert completed == 0


def test_longest_route_counts_length(game, state) -> None:
    player = state.players[0]
    player.claimed_route_ids = ["r3", "r10", "r12", "r14", "r16", "r18", "r20"]
    assert longest_route_length(player, game.routes_by_id) >= 13
