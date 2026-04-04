from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ttr_nsai.engine.models import CardColor, GameState, PlayerState, Route


@dataclass(frozen=True)
class ClaimCheck:
    legal: bool
    reason: str
    chosen_color: Optional[CardColor] = None
    color_cards_used: int = 0
    wild_cards_used: int = 0


def evaluate_claim(
    state: GameState,
    player: PlayerState,
    route: Route,
    chosen_color: Optional[CardColor],
) -> ClaimCheck:
    if any(route.route_id in other.claimed_route_ids for other in state.players):
        return ClaimCheck(legal=False, reason="Route already claimed.")
    if player.trains_remaining < route.length:
        return ClaimCheck(legal=False, reason="Not enough trains remaining.")

    if route.color is not None:
        effective_color = route.color if chosen_color is None else chosen_color
        if effective_color != route.color:
            return ClaimCheck(legal=False, reason="Colored route requires the printed route color.")
    else:
        if chosen_color is None or chosen_color == CardColor.WILD:
            return ClaimCheck(legal=False, reason="Gray routes require selecting one non-wild color.")
        effective_color = chosen_color

    color_count = player.hand.get(effective_color, 0)
    wild_count = player.hand.get(CardColor.WILD, 0)
    if color_count + wild_count < route.length:
        return ClaimCheck(
            legal=False,
            reason="Not enough cards in the selected color plus wild cards.",
            chosen_color=effective_color,
        )

    color_cards_used = min(color_count, route.length)
    wild_cards_used = route.length - color_cards_used
    return ClaimCheck(
        legal=True,
        reason="Legal claim.",
        chosen_color=effective_color,
        color_cards_used=color_cards_used,
        wild_cards_used=wild_cards_used,
    )
