from __future__ import annotations

import pytest

from ttr_nsai.engine.game import TicketToRideGame
from ttr_nsai.symbolic.reasoner import SymbolicReasoner


@pytest.fixture()
def game() -> TicketToRideGame:
    return TicketToRideGame(seed=7)


@pytest.fixture()
def state(game: TicketToRideGame):
    return game.initial_state(["Alice", "Bob"])


@pytest.fixture()
def reasoner(game: TicketToRideGame) -> SymbolicReasoner:
    return SymbolicReasoner(game.routes_by_id)
