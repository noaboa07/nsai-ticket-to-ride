from __future__ import annotations

from ttr_nsai.ai.base import BaseAgent
from ttr_nsai.engine.models import Action, ActionType, GameState
from ttr_nsai.symbolic.reasoner import SymbolicReasoner


def render_turn_summary(
    state: GameState,
    reasoner: SymbolicReasoner,
    reveal_all: bool = True,
    viewer_player_id: int | None = None,
) -> str:
    lines = [
        "",
        "=" * 72,
        f"Turn {state.turn_number} | Active: {state.active_player().name}",
        "-" * 72,
        "Players:",
    ]
    for player in state.players:
        card_summary = ", ".join(
            f"{color.value}:{count}"
            for color, count in sorted(player.hand.items(), key=lambda item: item[0].value)
            if count
        ) or "none"
        ticket_summary = ", ".join(
            f"{ticket.city1}-{ticket.city2}({ticket.points})" for ticket in player.tickets
        )
        progress = reasoner.average_ticket_progress(state, player)
        if not reveal_all and viewer_player_id is not None and player.player_id != viewer_player_id:
            ticket_summary = f"{len(player.tickets)} hidden ticket(s)"
        lines.append(
            f"  {player.name:<12} score={player.score:>3} trains={player.trains_remaining:>2} "
            f"ticket_progress={progress:>4.0%}"
        )
        lines.append(f"    cards: {card_summary}")
        lines.append(f"    tickets: {ticket_summary or 'none'}")

    lines.append("-" * 72)
    lines.append("Claimed routes:")
    for player in state.players:
        routes = [
            f"{state.route_by_id(route_id).city1}-{state.route_by_id(route_id).city2}"
            for route_id in player.claimed_route_ids
        ]
        lines.append(f"  {player.name:<12} {', '.join(routes) if routes else 'none'}")

    lines.append("-" * 72)
    lines.append("Available claim options:")
    any_routes = False
    active_player = state.active_player()
    for route in state.routes:
        colors = reasoner.claim_colors_for_route(state, active_player, route)
        if not colors:
            continue
        any_routes = True
        color_labels = []
        for color in colors:
            claim_check = reasoner.check_claim(state, active_player, route, color)
            color_labels.append(f"{color.value}({claim_check.color_cards_used}+{claim_check.wild_cards_used} wild)")
        route_color = route.color.value if route.color else "gray"
        lines.append(
            f"  {route.route_id:<3} {route.city1}-{route.city2:<18} len={route.length} pts={route.points} "
            f"base={route_color} using {', '.join(color_labels)}"
        )
    if not any_routes:
        lines.append("  none")
    lines.append("=" * 72)
    return "\n".join(lines)


def describe_action(state: GameState, action: Action, reasoner: SymbolicReasoner) -> str:
    if action.action_type == ActionType.DRAW_TRAIN_CARDS:
        return f"Draw 2 train cards | {reasoner.explain_action(state, action)}"
    if action.action_type == ActionType.DRAW_DESTINATIONS:
        keep = ",".join(str(index) for index in action.ticket_keep_indices)
        return f"Draw 2 destination tickets keep [{keep}] | {reasoner.explain_action(state, action)}"
    route = state.route_by_id(action.route_id or "")
    claim_check = reasoner.check_claim(state, state.active_player(), route, action.color)
    color = action.color.value if action.color else "none"
    return (
        f"Claim {route.route_id} {route.city1}-{route.city2} len={route.length} color={color} "
        f"cost={claim_check.color_cards_used}+{claim_check.wild_cards_used} wild | "
        f"{reasoner.explain_action(state, action)}"
    )


def render_last_decision(agent: BaseAgent) -> str:
    decision = agent.last_decision
    if not decision:
        return ""
    lines = [
        "Decision trace:",
        decision.trace or f"Chosen: {decision.action.action_type.value}",
    ]
    return "\n".join(lines)
