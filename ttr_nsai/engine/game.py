from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from time import perf_counter
from typing import Dict, List, Optional

from ttr_nsai.data.board import build_destination_tickets, build_routes, build_train_deck
from ttr_nsai.engine.models import Action, ActionType, CardColor, DestinationTicket, GameState, PlayerState, Route
from ttr_nsai.engine.rules import ClaimCheck, evaluate_claim
from ttr_nsai.engine.scoring import award_longest_route_bonus, score_tickets


class IllegalMoveError(ValueError):
    """Raised when an action violates the game rules."""


@dataclass
class TurnResult:
    action: Action
    explanation: str
    decision_time: float
    was_illegal: bool = False


class TicketToRideGame:
    def __init__(self, seed: Optional[int] = None) -> None:
        self.random = random.Random(seed)
        self.routes: List[Route] = build_routes()
        self.routes_by_id: Dict[str, Route] = {route.route_id: route for route in self.routes}

    def initial_state(self, player_names: Optional[List[str]] = None) -> GameState:
        names = player_names or ["Player 1", "Player 2"]
        train_deck = build_train_deck()
        destination_deck = build_destination_tickets()
        self.random.shuffle(train_deck)
        self.random.shuffle(destination_deck)
        players = [PlayerState(player_id=i, name=name, hand={color: 0 for color in CardColor}) for i, name in enumerate(names)]
        state = GameState(
            routes=copy.deepcopy(self.routes),
            players=players,
            train_deck=train_deck,
            train_discard=[],
            destination_deck=destination_deck,
        )
        for player in state.players:
            self._draw_train_cards(state, player, 4)
            player.tickets.extend(self._draw_destination_cards(state, 2))
        return state

    def clone_state(self, state: GameState) -> GameState:
        return copy.deepcopy(state)

    def apply_action(self, state: GameState, action: Action) -> str:
        player = state.active_player()
        if state.game_over:
            raise IllegalMoveError("Game is already over.")

        if action.action_type == ActionType.DRAW_TRAIN_CARDS:
            cards = self._draw_train_cards(state, player, 2)
            explanation = f"{player.name} drew train cards: {', '.join(card.value for card in cards)}."
        elif action.action_type == ActionType.DRAW_DESTINATIONS:
            options = self._draw_destination_cards(state, 2)
            if not options:
                raise IllegalMoveError("No destination tickets remain.")
            keep_indices = action.ticket_keep_indices or (0,)
            if any(index < 0 or index >= len(options) for index in keep_indices):
                raise IllegalMoveError("Invalid destination ticket selection.")
            kept = [options[index] for index in sorted(set(keep_indices))]
            player.tickets.extend(kept)
            explanation = f"{player.name} kept destination tickets: {', '.join(f'{t.city1}-{t.city2}' for t in kept)}."
        elif action.action_type == ActionType.CLAIM_ROUTE:
            if not action.route_id:
                raise IllegalMoveError("Route id is required to claim a route.")
            route = state.route_by_id(action.route_id)
            self._claim_route(state, player, route, action.color)
            explanation = f"{player.name} claimed {route.city1}-{route.city2} for {route.points} points."
        else:
            raise IllegalMoveError(f"Unsupported action type: {action.action_type}")

        state.action_log.append(explanation)
        self._advance_turn(state)
        return explanation

    def execute_turn(self, state: GameState, agent: "AgentProtocol") -> TurnResult:
        state_before = self.clone_state(state)
        start = perf_counter()
        action = agent.choose_action(state_before)
        decision_time = perf_counter() - start
        try:
            explanation = self.apply_action(state, action)
            return TurnResult(action=action, explanation=explanation, decision_time=decision_time)
        except IllegalMoveError:
            state.active_player().illegal_move_attempts += 1
            fallback = Action(ActionType.DRAW_TRAIN_CARDS)
            explanation = self.apply_action(state, fallback)
            return TurnResult(action=fallback, explanation=explanation, decision_time=decision_time, was_illegal=True)

    def finalize_game(self, state: GameState) -> None:
        if state.winner is not None:
            return
        for player in state.players:
            ticket_score, _ = score_tickets(player, self.routes_by_id)
            player.score += ticket_score
        award_longest_route_bonus(state.players, self.routes_by_id)
        best_score = max(player.score for player in state.players)
        contenders = [player for player in state.players if player.score == best_score]
        if len(contenders) == 1:
            state.winner = contenders[0].player_id
        else:
            completion_counts = {player.player_id: score_tickets(player, self.routes_by_id)[1] for player in contenders}
            best_completion = max(completion_counts.values())
            refined = [player for player in contenders if completion_counts[player.player_id] == best_completion]
            state.winner = min(player.player_id for player in refined)
        state.game_over = True

    def _draw_train_cards(self, state: GameState, player: PlayerState, count: int) -> List[CardColor]:
        cards: List[CardColor] = []
        for _ in range(count):
            if not state.train_deck:
                if not state.train_discard:
                    break
                self.random.shuffle(state.train_discard)
                state.train_deck = state.train_discard
                state.train_discard = []
            card = state.train_deck.pop()
            player.hand[card] = player.hand.get(card, 0) + 1
            cards.append(card)
        return cards

    def _draw_destination_cards(self, state: GameState, count: int) -> List[DestinationTicket]:
        cards: List[DestinationTicket] = []
        for _ in range(count):
            if not state.destination_deck:
                break
            cards.append(state.destination_deck.pop())
        return cards

    def _claim_route(self, state: GameState, player: PlayerState, route: Route, chosen_color: Optional[CardColor]) -> None:
        claim_check = self.check_route_claim(state, player, route, chosen_color)
        if not claim_check.legal or claim_check.chosen_color is None:
            raise IllegalMoveError(claim_check.reason)

        player.hand[claim_check.chosen_color] -= claim_check.color_cards_used
        player.hand[CardColor.WILD] -= claim_check.wild_cards_used
        state.train_discard.extend([claim_check.chosen_color] * claim_check.color_cards_used)
        state.train_discard.extend([CardColor.WILD] * claim_check.wild_cards_used)
        player.claimed_route_ids.append(route.route_id)
        player.trains_remaining -= route.length
        player.score += route.points

    def check_route_claim(
        self,
        state: GameState,
        player: PlayerState,
        route: Route,
        chosen_color: Optional[CardColor],
    ) -> ClaimCheck:
        return evaluate_claim(state, player, route, chosen_color)

    def _advance_turn(self, state: GameState) -> None:
        player = state.active_player()
        if not state.last_round_triggered and player.trains_remaining <= 2:
            state.last_round_triggered = True
            state.final_turns_remaining = len(state.players)

        if state.last_round_triggered:
            assert state.final_turns_remaining is not None
            state.final_turns_remaining -= 1
            if state.final_turns_remaining <= 0:
                self.finalize_game(state)
                return

        state.current_player = (state.current_player + 1) % len(state.players)
        state.turn_number += 1


class AgentProtocol:
    def choose_action(self, state: GameState) -> Action:
        raise NotImplementedError
