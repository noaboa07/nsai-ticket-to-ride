from __future__ import annotations

import heapq
from dataclasses import dataclass
from math import inf
from typing import Dict, Iterable, List, Optional

from ttr_nsai.engine.models import Action, ActionType, CardColor, DestinationTicket, GameState, PlayerState, Route
from ttr_nsai.engine.rules import ClaimCheck, evaluate_claim
from ttr_nsai.engine.scoring import is_ticket_completed


@dataclass(frozen=True)
class StrategicAssessment:
    action: Action
    legal: bool
    base_score: float
    explanation: str
    tags: tuple[str, ...]
    heuristic_score: float = 0.0
    symbolic_adjustment: float = 0.0
    ticket_progress_delta: float = 0.0
    opponent_block_delta: float = 0.0


class SymbolicReasoner:
    def __init__(self, routes_by_id: Dict[str, Route]) -> None:
        self.routes_by_id = routes_by_id
        self.routes = list(routes_by_id.values())
        self._baseline_ticket_distances = self._build_baseline_distances()

    def legal_actions(self, state: GameState, player: Optional[PlayerState] = None) -> List[Action]:
        player = player or state.active_player()
        actions: List[Action] = [Action(ActionType.DRAW_TRAIN_CARDS)]
        if state.destination_deck:
            actions.append(Action(ActionType.DRAW_DESTINATIONS, ticket_keep_indices=(0,)))
            if len(state.destination_deck) >= 2:
                actions.append(Action(ActionType.DRAW_DESTINATIONS, ticket_keep_indices=(0, 1)))

        for route in state.routes:
            for color in self.claim_colors_for_route(state, player, route):
                actions.append(Action(ActionType.CLAIM_ROUTE, route_id=route.route_id, color=color))
        return actions

    def claim_colors_for_route(self, state: GameState, player: PlayerState, route: Route) -> List[CardColor]:
        candidate_colors = [route.color] if route.color is not None else [color for color in CardColor if color != CardColor.WILD]
        legal_colors: List[CardColor] = []
        for color in candidate_colors:
            if color is None:
                continue
            check = self.check_claim(state, player, route, color)
            if check.legal:
                legal_colors.append(color)
        return legal_colors

    def check_claim(
        self,
        state: GameState,
        player: PlayerState,
        route: Route,
        chosen_color: Optional[CardColor],
    ) -> ClaimCheck:
        return evaluate_claim(state, player, route, chosen_color)

    def is_legal(self, state: GameState, action: Action, player: Optional[PlayerState] = None) -> bool:
        player = player or state.active_player()
        if action.action_type == ActionType.DRAW_TRAIN_CARDS:
            return True
        if action.action_type == ActionType.DRAW_DESTINATIONS:
            if not state.destination_deck:
                return False
            keep_indices = action.ticket_keep_indices or (0,)
            preview_count = min(2, len(state.destination_deck))
            return bool(keep_indices) and all(0 <= index < preview_count for index in keep_indices)
        if action.action_type == ActionType.CLAIM_ROUTE and action.route_id:
            route = self.routes_by_id[action.route_id]
            return self.check_claim(state, player, route, action.color).legal
        return False

    def action_label(self, state: GameState, action: Action) -> str:
        if action.action_type == ActionType.DRAW_TRAIN_CARDS:
            return "Draw 2 train cards"
        if action.action_type == ActionType.DRAW_DESTINATIONS:
            keep = ",".join(str(index) for index in action.ticket_keep_indices)
            return f"Draw destination tickets keep=[{keep}]"
        route = self.routes_by_id[action.route_id or ""]
        color = action.color.value if action.color else "none"
        return f"Claim {route.city1}-{route.city2} ({route.route_id}, {color}, len={route.length})"

    def explain_action(self, state: GameState, action: Action, player: Optional[PlayerState] = None) -> str:
        player = player or state.active_player()
        if action.action_type == ActionType.DRAW_TRAIN_CARDS:
            claimable_routes = self._claimable_routes(state, player)
            if not claimable_routes:
                needed = self._best_unaffordable_ticket_route(state, player)
                if needed:
                    route, color = needed
                    color_label = route.color.value if route.color else color.value
                    return f"Draw train cards because no route is currently claimable and {route.city1}-{route.city2} needs more {color_label} cards."
                return "Draw train cards because no productive route is currently claimable."
            best_route = max(claimable_routes, key=lambda route: self.ticket_progress_delta(state, player, route))
            if self.ticket_progress_delta(state, player, best_route) <= 0:
                return "Draw train cards because current claimable routes do not improve ticket progress enough."
            return f"Draw train cards to prepare for ticket-advancing routes such as {best_route.city1}-{best_route.city2}."

        if action.action_type == ActionType.DRAW_DESTINATIONS:
            return "Draw destination tickets because the current network is stable enough to support another goal."

        route = self.routes_by_id[action.route_id or ""]
        ticket_delta = self.ticket_progress_delta(state, player, route)
        block_delta = self.blocking_value(state, player, route)
        route_value = route.points
        reasons: List[str] = [f"Claim {route.city1}-{route.city2} for {route_value} route points"]
        if ticket_delta > 0:
            reasons.append(f"it reduces remaining ticket distance by {ticket_delta:.1f}")
        if block_delta > 0:
            reasons.append(f"it blocks about {block_delta:.1f} opponent progress")
        if ticket_delta <= 0 and route.length >= 3:
            reasons.append("it is still a strong standalone route")
        if ticket_delta <= 0 and block_delta <= 0 and route.points < 4:
            reasons.append("it is mostly a low-impact connector")
        return " because ".join([reasons[0], ", ".join(reasons[1:])]) if len(reasons) > 1 else reasons[0] + "."

    def assess_action(self, state: GameState, action: Action, player: Optional[PlayerState] = None) -> StrategicAssessment:
        player = player or state.active_player()
        if not self.is_legal(state, action, player):
            return StrategicAssessment(action=action, legal=False, base_score=-1e9, explanation="Illegal move.", tags=("illegal",))

        tags: List[str] = []
        base_score = 0.0
        ticket_delta = 0.0
        block_delta = 0.0
        if action.action_type == ActionType.DRAW_TRAIN_CARDS:
            base_score += 2.0
            if not self._claimable_routes(state, player):
                base_score += 3.0
                tags.append("no-claim")
            if self._needs_cards_for_tickets(state, player):
                base_score += 2.5
                tags.append("setup")
        elif action.action_type == ActionType.DRAW_DESTINATIONS:
            base_score += 1.0
            if self._ticket_capacity(player) > 0:
                base_score += 2.0
                tags.append("expansion")
            else:
                base_score -= 2.0
        elif action.action_type == ActionType.CLAIM_ROUTE:
            route = self.routes_by_id[action.route_id or ""]
            ticket_delta = self.ticket_progress_delta(state, player, route)
            block_delta = self.blocking_value(state, player, route)
            base_score += route.points * 1.2
            base_score += ticket_delta * 3.5
            base_score += min(block_delta, 4.0) * 1.5
            if ticket_delta > 0:
                tags.append("ticket")
            if block_delta > 0:
                tags.append("block")
            if route.length >= 3:
                base_score += 1.0
                tags.append("long")
            if player.trains_remaining <= 5:
                base_score += route.points
                tags.append("endgame")
            if ticket_delta <= 0 and block_delta <= 0 and route.points < 4:
                base_score -= 2.5
                tags.append("off-plan")

        symbolic_adjustment = self.strategic_adjustment(state, action, player)
        total = base_score + symbolic_adjustment
        return StrategicAssessment(
            action=action,
            legal=True,
            base_score=total,
            explanation=self.explain_action(state, action, player),
            tags=tuple(tags),
            heuristic_score=base_score,
            symbolic_adjustment=symbolic_adjustment,
            ticket_progress_delta=ticket_delta,
            opponent_block_delta=block_delta,
        )

    def strategic_adjustment(self, state: GameState, action: Action, player: Optional[PlayerState] = None) -> float:
        player = player or state.active_player()
        if action.action_type == ActionType.DRAW_TRAIN_CARDS:
            return 1.5 if not self._claimable_routes(state, player) else 0.0
        if action.action_type == ActionType.DRAW_DESTINATIONS:
            return -3.0 if self._ticket_capacity(player) <= 0 else 0.5

        route = self.routes_by_id[action.route_id or ""]
        adjustment = 0.0
        ticket_delta = self.ticket_progress_delta(state, player, route)
        block_delta = self.blocking_value(state, player, route)
        if ticket_delta >= 2.0:
            adjustment += 2.0
        if block_delta >= 2.0:
            adjustment += 1.5
        if ticket_delta <= 0 and block_delta <= 0:
            adjustment -= 2.0
        if len(player.tickets) >= 3 and ticket_delta <= 0:
            adjustment -= 1.0
        return adjustment

    def ticket_progress_delta(self, state: GameState, player: PlayerState, route: Route) -> float:
        total_delta = 0.0
        for ticket in player.tickets:
            if is_ticket_completed(player, ticket, self.routes_by_id):
                continue
            before = self._remaining_ticket_distance(state, player, ticket)
            after = self._remaining_ticket_distance(state, player, ticket, extra_owned_route=route.route_id)
            if before == inf and after < inf:
                total_delta += 5.0
            elif before < inf and after < inf:
                total_delta += max(0.0, before - after)
        return total_delta

    def average_ticket_progress(self, state: GameState, player: PlayerState) -> float:
        if not player.tickets:
            return 1.0
        progresses = [self.ticket_completion_progress(state, player, ticket) for ticket in player.tickets]
        return sum(progresses) / len(progresses)

    def ticket_completion_progress(self, state: GameState, player: PlayerState, ticket: DestinationTicket) -> float:
        if is_ticket_completed(player, ticket, self.routes_by_id):
            return 1.0
        baseline = self._baseline_ticket_distances.get((ticket.city1, ticket.city2), inf)
        if baseline == inf or baseline <= 0:
            return 0.0
        remaining = self._remaining_ticket_distance(state, player, ticket)
        if remaining == inf:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (remaining / baseline)))

    def blocking_value(self, state: GameState, player: PlayerState, route: Route) -> float:
        opponent = next(other for other in state.players if other.player_id != player.player_id)
        return self.ticket_progress_delta(state, opponent, route)

    def prevented_illegal_claims(self, state: GameState, player: Optional[PlayerState] = None) -> int:
        player = player or state.active_player()
        prevented = 0
        for route in state.routes:
            candidate_colors = [route.color] if route.color is not None else [color for color in CardColor if color != CardColor.WILD]
            for color in candidate_colors:
                if color is None:
                    continue
                if not self.check_claim(state, player, route, color).legal:
                    prevented += 1
        return prevented

    def _claimable_routes(self, state: GameState, player: PlayerState) -> List[Route]:
        routes: List[Route] = []
        for route in state.routes:
            if self.claim_colors_for_route(state, player, route):
                routes.append(route)
        return routes

    def _needs_cards_for_tickets(self, state: GameState, player: PlayerState) -> bool:
        return any(
            not is_ticket_completed(player, ticket, self.routes_by_id) for ticket in player.tickets
        ) and not self._claimable_routes(state, player)

    def _ticket_capacity(self, player: PlayerState) -> int:
        return 1 if len(player.tickets) <= 2 and player.trains_remaining >= 8 else 0

    def _best_unaffordable_ticket_route(self, state: GameState, player: PlayerState) -> Optional[tuple[Route, CardColor]]:
        best: Optional[tuple[float, Route, CardColor]] = None
        for route in state.routes:
            if any(route.route_id in other.claimed_route_ids for other in state.players):
                continue
            ticket_delta = self.ticket_progress_delta(state, player, route)
            if ticket_delta <= 0:
                continue
            candidate_colors = [route.color] if route.color is not None else [color for color in CardColor if color != CardColor.WILD]
            for color in candidate_colors:
                if color is None:
                    continue
                check = self.check_claim(state, player, route, color)
                if check.legal:
                    continue
                value = ticket_delta * 10 + route.points
                if best is None or value > best[0]:
                    best = (value, route, color)
        if best is None:
            return None
        return best[1], best[2]

    def _remaining_ticket_distance(
        self,
        state: GameState,
        player: PlayerState,
        ticket: DestinationTicket,
        extra_owned_route: Optional[str] = None,
    ) -> float:
        return self._shortest_distance(
            state,
            player,
            ticket.city1,
            ticket.city2,
            extra_owned_route=extra_owned_route,
        )

    def _shortest_distance(
        self,
        state: GameState,
        player: PlayerState,
        start: str,
        goal: str,
        extra_owned_route: Optional[str] = None,
    ) -> float:
        if start == goal:
            return 0.0
        owned_routes = set(player.claimed_route_ids)
        if extra_owned_route:
            owned_routes.add(extra_owned_route)
        blocked_routes = {
            route_id
            for other in state.players
            if other.player_id != player.player_id
            for route_id in other.claimed_route_ids
        }

        queue: list[tuple[float, str]] = [(0.0, start)]
        best_distance: Dict[str, float] = {start: 0.0}
        while queue:
            distance, city = heapq.heappop(queue)
            if city == goal:
                return distance
            if distance > best_distance.get(city, inf):
                continue
            for route in self.routes:
                if route.route_id in blocked_routes and route.route_id not in owned_routes:
                    continue
                if city not in (route.city1, route.city2):
                    continue
                neighbor = route.city2 if city == route.city1 else route.city1
                edge_cost = 0.0 if route.route_id in owned_routes else float(route.length)
                new_distance = distance + edge_cost
                if new_distance < best_distance.get(neighbor, inf):
                    best_distance[neighbor] = new_distance
                    heapq.heappush(queue, (new_distance, neighbor))
        return inf

    def _build_baseline_distances(self) -> Dict[tuple[str, str], float]:
        distances: Dict[tuple[str, str], float] = {}
        cities = sorted({city for route in self.routes for city in (route.city1, route.city2)})
        dummy_state = GameState(routes=self.routes, players=[], train_deck=[], train_discard=[], destination_deck=[])
        dummy_player = PlayerState(player_id=0, name="baseline", hand={}, tickets=[])
        for city1 in cities:
            for city2 in cities:
                if city1 == city2:
                    continue
                distances[(city1, city2)] = self._shortest_distance(dummy_state, dummy_player, city1, city2)
        return distances
