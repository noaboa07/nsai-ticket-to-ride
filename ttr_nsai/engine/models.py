from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class CardColor(str, Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    BLACK = "black"
    WHITE = "white"
    WILD = "wild"


class ActionType(str, Enum):
    DRAW_TRAIN_CARDS = "draw_train_cards"
    DRAW_DESTINATIONS = "draw_destinations"
    CLAIM_ROUTE = "claim_route"


CITY_NAMES: Tuple[str, ...] = (
    "Alder",
    "Benton",
    "Cedar",
    "Dover",
    "Elm",
    "Fairview",
    "Grafton",
    "Harbor",
    "Irons",
    "Juniper",
    "Kingston",
    "Lakeside",
)


@dataclass(frozen=True)
class Route:
    route_id: str
    city1: str
    city2: str
    color: Optional[CardColor]
    length: int
    points: int


@dataclass(frozen=True)
class DestinationTicket:
    ticket_id: str
    city1: str
    city2: str
    points: int


@dataclass
class PlayerState:
    player_id: int
    name: str
    hand: Dict[CardColor, int] = field(default_factory=dict)
    tickets: List[DestinationTicket] = field(default_factory=list)
    claimed_route_ids: List[str] = field(default_factory=list)
    score: int = 0
    trains_remaining: int = 20
    illegal_move_attempts: int = 0

    def total_cards(self) -> int:
        return sum(self.hand.values())


@dataclass(frozen=True)
class Action:
    action_type: ActionType
    route_id: Optional[str] = None
    color: Optional[CardColor] = None
    ticket_keep_indices: Tuple[int, ...] = ()


@dataclass
class GameState:
    routes: List[Route]
    players: List[PlayerState]
    train_deck: List[CardColor]
    train_discard: List[CardColor]
    destination_deck: List[DestinationTicket]
    current_player: int = 0
    turn_number: int = 1
    last_round_triggered: bool = False
    final_turns_remaining: Optional[int] = None
    winner: Optional[int] = None
    game_over: bool = False
    action_log: List[str] = field(default_factory=list)

    def active_player(self) -> PlayerState:
        return self.players[self.current_player]

    def route_by_id(self, route_id: str) -> Route:
        for route in self.routes:
            if route.route_id == route_id:
                return route
        raise KeyError(f"Unknown route_id={route_id}")
