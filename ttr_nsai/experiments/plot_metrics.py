from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt


def _load_rows(csv_path: Path) -> List[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def generate_plots(csv_path: Path, output_dir: Path) -> list[Path]:
    rows = _load_rows(csv_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    by_agent: Dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        agent = row["agent_name"]
        for metric in (
            "won",
            "score",
            "ticket_completion_rate",
            "tickets_completed",
            "avg_ticket_progress",
            "avg_route_points",
            "avg_decision_time_ms",
            "prevented_illegal_claims_avg",
            "game_length_turns",
        ):
            key = "win_rate" if metric == "won" else metric
            by_agent[agent][key].append(float(row[metric]))

    metrics = [
        "win_rate",
        "score",
        "ticket_completion_rate",
        "tickets_completed",
        "avg_ticket_progress",
        "avg_route_points",
        "avg_decision_time_ms",
        "prevented_illegal_claims_avg",
        "game_length_turns",
    ]
    plot_paths: list[Path] = []
    for metric in metrics:
        agents = list(by_agent.keys())
        values = [sum(by_agent[agent][metric]) / max(1, len(by_agent[agent][metric])) for agent in agents]
        plt.figure(figsize=(8, 4.5))
        plt.bar(agents, values, color=["#5b8c5a", "#e07a5f", "#3d405b"][: len(agents)])
        plt.title(metric.replace("_", " ").title())
        plt.ylabel(metric.replace("_", " ").title())
        plt.tight_layout()
        plot_path = output_dir / f"{metric}.png"
        plt.savefig(plot_path)
        plt.close()
        plot_paths.append(plot_path)
    return plot_paths
