from __future__ import annotations

import argparse

from ttr_nsai.ai.base import AgentDecision, BaseAgent
from ttr_nsai.engine.models import Action, ActionType, GameState
from ttr_nsai.symbolic.reasoner import SymbolicReasoner
from ttr_nsai.ui.rendering import describe_action, render_last_decision, render_turn_summary


class HumanCLIPlayer(BaseAgent):
    name = "human"

    def __init__(self, reasoner: SymbolicReasoner, trace_mode: bool = False) -> None:
        super().__init__()
        self.reasoner = reasoner
        self.trace_mode = trace_mode

    def decide(self, state: GameState) -> AgentDecision:
        legal_actions = self.reasoner.legal_actions(state)
        print("\nAvailable actions:")
        for index, action in enumerate(legal_actions):
            print(f"  [{index:02d}] {describe_action(state, action, self.reasoner)}")
        while True:
            raw = input("Choose action number: ").strip()
            if raw.isdigit() and int(raw) < len(legal_actions):
                action = legal_actions[int(raw)]
                explanation = self.reasoner.explain_action(state, action)
                trace = f"Chosen: {self.reasoner.action_label(state, action)}\nWhy: {explanation}"
                return AgentDecision(action=action, explanation=explanation, score=0.0, trace=trace)
            print("Invalid choice. Please enter one of the listed action numbers.")

def play_cli(agent_name: str, seed: int | None = None, trace_mode: bool = False) -> None:
    from ttr_nsai.ai.factory import build_agent
    from ttr_nsai.engine.game import TicketToRideGame
    from ttr_nsai.engine.scoring import score_tickets

    game = TicketToRideGame(seed=seed)
    state = game.initial_state(["Human", agent_name.title() + " AI"])
    reasoner = SymbolicReasoner(game.routes_by_id)
    human = HumanCLIPlayer(reasoner, trace_mode=trace_mode)
    ai_agent = build_agent(agent_name, reasoner)
    agents = [human, ai_agent]

    while not state.game_over:
        acting_player = state.current_player
        result = game.execute_turn(state, agents[acting_player])
        current_agent = agents[acting_player]
        print(f"\n{result.explanation}")
        if acting_player == 1 or trace_mode:
            print(render_last_decision(current_agent))
        if not state.game_over:
            print(render_turn_summary(state, reasoner, reveal_all=False, viewer_player_id=0))

    print("\nFinal state")
    print(render_turn_summary(state, reasoner, reveal_all=True, viewer_player_id=0))
    for player in state.players:
        ticket_score, completed = score_tickets(player, game.routes_by_id)
        print(
            f"{player.name}: final score={player.score}, ticket net={ticket_score}, "
            f"completed={completed}/{len(player.tickets)}"
        )
    print(f"Winner: {state.players[state.winner].name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Play simplified Ticket to Ride in the terminal.")
    parser.add_argument("--agent", choices=["random", "symbolic", "hybrid"], default="hybrid")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--trace", action="store_true", help="Show compact decision traces every turn.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    play_cli(agent_name=args.agent, seed=args.seed, trace_mode=args.trace)


if __name__ == "__main__":
    main()
