from __future__ import annotations

from ttr_nsai.symbolic.reasoner import SymbolicReasoner
from ttr_nsai.ui.rendering import render_turn_summary


def test_turn_summary_shows_human_tickets_and_hides_ai_tickets(game, state) -> None:
    reasoner = SymbolicReasoner(game.routes_by_id)
    state.current_player = 1
    summary = render_turn_summary(state, reasoner, reveal_all=False, viewer_player_id=0)
    human_ticket = f"{state.players[0].tickets[0].city1}-{state.players[0].tickets[0].city2}"
    assert human_ticket in summary
    assert "hidden ticket(s)" in summary
