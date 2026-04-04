from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from ttr_nsai.ai.factory import build_agent
from ttr_nsai.engine.game import TicketToRideGame
from ttr_nsai.engine.scoring import score_tickets
from ttr_nsai.symbolic.reasoner import SymbolicReasoner


@dataclass
class GameMetric:
    matchup: str
    seed: int
    player_name: str
    agent_name: str
    won: int
    score: int
    tickets_completed: int
    tickets_total: int
    ticket_completion_rate: float
    avg_ticket_progress: float
    avg_route_points: float
    claimed_routes: int
    avg_decision_time_ms: float
    illegal_move_count: int
    prevented_illegal_claims_avg: float
    game_length_turns: int


def play_match(agent_a_name: str, agent_b_name: str, seed: int) -> tuple[List[GameMetric], str]:
    game = TicketToRideGame(seed=seed)
    state = game.initial_state([agent_a_name, agent_b_name])
    reasoner = SymbolicReasoner(game.routes_by_id)
    agents = [build_agent(agent_a_name, reasoner), build_agent(agent_b_name, reasoner)]
    decision_times: list[list[float]] = [[], []]
    ticket_progress_samples: list[list[float]] = [[], []]
    prevented_illegal_samples: list[list[float]] = [[], []]
    trace_lines = [f"Matchup: {agent_a_name} vs {agent_b_name}", f"Seed: {seed}", ""]

    while not state.game_over:
        player_index = state.current_player
        player = state.players[player_index]
        ticket_progress_samples[player_index].append(reasoner.average_ticket_progress(state, player))
        prevented_illegal_samples[player_index].append(reasoner.prevented_illegal_claims(state, player))
        result = game.execute_turn(state, agents[player_index])
        decision_times[player_index].append(result.decision_time * 1000.0)
        decision = agents[player_index].last_decision
        trace_lines.append(
            f"Turn {state.turn_number - (0 if state.game_over else 1)} | {player.name} | {result.explanation}"
        )
        if decision:
            trace_lines.append(decision.trace or decision.explanation)
        trace_lines.append("")

    metrics: List[GameMetric] = []
    matchup = f"{agent_a_name}_vs_{agent_b_name}"
    game_length_turns = state.turn_number - 1
    for idx, player in enumerate(state.players):
        _, completed = score_tickets(player, game.routes_by_id)
        completion_rate = completed / len(player.tickets) if player.tickets else 0.0
        route_points = [game.routes_by_id[route_id].points for route_id in player.claimed_route_ids]
        metrics.append(
            GameMetric(
                matchup=matchup,
                seed=seed,
                player_name=player.name,
                agent_name=agents[idx].name,
                won=1 if state.winner == idx else 0,
                score=player.score,
                tickets_completed=completed,
                tickets_total=len(player.tickets),
                ticket_completion_rate=completion_rate,
                avg_ticket_progress=statistics.mean(ticket_progress_samples[idx]) if ticket_progress_samples[idx] else 0.0,
                avg_route_points=statistics.mean(route_points) if route_points else 0.0,
                claimed_routes=len(player.claimed_route_ids),
                avg_decision_time_ms=statistics.mean(decision_times[idx]) if decision_times[idx] else 0.0,
                illegal_move_count=player.illegal_move_attempts,
                prevented_illegal_claims_avg=statistics.mean(prevented_illegal_samples[idx]) if prevented_illegal_samples[idx] else 0.0,
                game_length_turns=game_length_turns,
            )
        )

    trace_lines.append("Final scores:")
    for player in state.players:
        trace_lines.append(f"- {player.name}: {player.score}")
    trace_lines.append(f"Winner: {state.players[state.winner].name}")
    return metrics, "\n".join(trace_lines)


def write_csv(rows: List[GameMetric], csv_path: Path) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(GameMetric.__annotations__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_summary(
    rows: List[GameMetric],
    summary_path: Path,
    *,
    start_seed: int,
    games_per_matchup: int,
    agent_names: list[str],
    trace_file: Optional[str],
) -> None:
    by_agent: dict[str, list[GameMetric]] = {}
    for row in rows:
        by_agent.setdefault(row.agent_name, []).append(row)

    summary = {
        "config": {
            "start_seed": start_seed,
            "games_per_matchup": games_per_matchup,
            "agents": agent_names,
            "trace_file": trace_file,
        },
        "agents": {
            agent_name: {
                "games": len(agent_rows),
                "win_rate": statistics.mean(row.won for row in agent_rows),
                "avg_score": statistics.mean(row.score for row in agent_rows),
                "avg_ticket_completion_rate": statistics.mean(row.ticket_completion_rate for row in agent_rows),
                "avg_tickets_completed": statistics.mean(row.tickets_completed for row in agent_rows),
                "avg_ticket_progress": statistics.mean(row.avg_ticket_progress for row in agent_rows),
                "avg_route_points": statistics.mean(row.avg_route_points for row in agent_rows),
                "avg_claimed_routes": statistics.mean(row.claimed_routes for row in agent_rows),
                "avg_decision_time_ms": statistics.mean(row.avg_decision_time_ms for row in agent_rows),
                "avg_game_length_turns": statistics.mean(row.game_length_turns for row in agent_rows),
                "avg_prevented_illegal_claims": statistics.mean(row.prevented_illegal_claims_avg for row in agent_rows),
                "illegal_move_rejections": sum(row.illegal_move_count for row in agent_rows),
            }
            for agent_name, agent_rows in by_agent.items()
        },
    }
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)


def run_tournament(
    agent_names: Iterable[str],
    games_per_matchup: int,
    output_dir: Path,
    *,
    start_seed: int = 1,
    trace_filename: str | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: List[GameMetric] = []
    names = list(agent_names)
    seed = start_seed
    saved_trace = False
    trace_path = output_dir / trace_filename if trace_filename else None

    for agent_a in names:
        for agent_b in names:
            if agent_a == agent_b:
                continue
            for _ in range(games_per_matchup):
                metrics, trace_text = play_match(agent_a, agent_b, seed)
                rows.extend(metrics)
                if trace_path is not None and not saved_trace:
                    trace_path.write_text(trace_text, encoding="utf-8")
                    saved_trace = True
                seed += 1

    csv_path = output_dir / "metrics.csv"
    json_path = output_dir / "summary.json"
    write_csv(rows, csv_path)
    write_summary(
        rows,
        json_path,
        start_seed=start_seed,
        games_per_matchup=games_per_matchup,
        agent_names=names,
        trace_file=trace_filename,
    )
    return csv_path, json_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run automated experiments for Ticket to Ride agents.")
    parser.add_argument("--games", type=int, default=20, help="Games per ordered matchup.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--agents", nargs="+", default=["random", "symbolic", "hybrid"])
    parser.add_argument("--seed", type=int, default=1, help="Starting seed for reproducible experiment runs.")
    parser.add_argument(
        "--trace-file",
        default=None,
        help="Optional filename for one sample gameplay/decision trace written inside the output directory.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    start = time.perf_counter()
    csv_path, json_path = run_tournament(
        args.agents,
        args.games,
        args.output_dir,
        start_seed=args.seed,
        trace_filename=args.trace_file,
    )
    from ttr_nsai.experiments.plot_metrics import generate_plots

    plot_paths = generate_plots(csv_path, args.output_dir)
    elapsed = time.perf_counter() - start
    print(f"Saved metrics to {csv_path}")
    print(f"Saved summary to {json_path}")
    if args.trace_file:
        print(f"Saved sample trace to {args.output_dir / args.trace_file}")
    for path in plot_paths:
        print(f"Generated plot: {path}")
    print(f"Completed in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
