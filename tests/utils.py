from __future__ import annotations

from ttr_nsai.engine.models import CardColor


def clear_hands(state) -> None:
    for player in state.players:
        for color in CardColor:
            player.hand[color] = 0
