from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, Set

from ttr_nsai.engine.models import DestinationTicket, PlayerState, Route


def build_player_graph(player: PlayerState, routes_by_id: Dict[str, Route]) -> Dict[str, Set[str]]:
    graph: Dict[str, Set[str]] = defaultdict(set)
    for route_id in player.claimed_route_ids:
        route = routes_by_id[route_id]
        graph[route.city1].add(route.city2)
        graph[route.city2].add(route.city1)
    return graph


def is_ticket_completed(player: PlayerState, ticket: DestinationTicket, routes_by_id: Dict[str, Route]) -> bool:
    graph = build_player_graph(player, routes_by_id)
    if ticket.city1 == ticket.city2:
        return True
    if ticket.city1 not in graph or ticket.city2 not in graph:
        return False
    queue = deque([ticket.city1])
    seen = {ticket.city1}
    while queue:
        city = queue.popleft()
        if city == ticket.city2:
            return True
        for neighbor in graph[city]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return False


def score_tickets(player: PlayerState, routes_by_id: Dict[str, Route]) -> tuple[int, int]:
    completed = 0
    ticket_score = 0
    for ticket in player.tickets:
        if is_ticket_completed(player, ticket, routes_by_id):
            completed += 1
            ticket_score += ticket.points
        else:
            ticket_score -= ticket.points
    return ticket_score, completed


def longest_route_length(player: PlayerState, routes_by_id: Dict[str, Route]) -> int:
    adjacency: Dict[str, list[tuple[str, str]]] = defaultdict(list)
    for route_id in player.claimed_route_ids:
        route = routes_by_id[route_id]
        adjacency[route.city1].append((route.city2, route.route_id))
        adjacency[route.city2].append((route.city1, route.route_id))

    best = 0

    def dfs(city: str, used_routes: Set[str], total: int) -> None:
        nonlocal best
        best = max(best, total)
        for next_city, route_id in adjacency[city]:
            if route_id in used_routes:
                continue
            used_routes.add(route_id)
            dfs(next_city, used_routes, total + routes_by_id[route_id].length)
            used_routes.remove(route_id)

    for city in adjacency:
        dfs(city, set(), 0)
    return best


def award_longest_route_bonus(players: Iterable[PlayerState], routes_by_id: Dict[str, Route], bonus: int = 10) -> None:
    lengths = {player.player_id: longest_route_length(player, routes_by_id) for player in players}
    if not lengths:
        return
    best = max(lengths.values())
    for player in players:
        if lengths[player.player_id] == best and best > 0:
            player.score += bonus
