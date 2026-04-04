from __future__ import annotations

from ttr_nsai.ai.base import BaseAgent
from ttr_nsai.ai.hybrid_agent import HybridNeuroSymbolicAgent
from ttr_nsai.ai.random_agent import RandomAgent
from ttr_nsai.ai.symbolic_agent import SymbolicHeuristicAgent
from ttr_nsai.symbolic.reasoner import SymbolicReasoner


def build_agent(agent_name: str, reasoner: SymbolicReasoner) -> BaseAgent:
    normalized = agent_name.lower()
    if normalized == "random":
        return RandomAgent(reasoner)
    if normalized == "symbolic":
        return SymbolicHeuristicAgent(reasoner)
    if normalized == "hybrid":
        return HybridNeuroSymbolicAgent(reasoner)
    raise ValueError(f"Unknown agent: {agent_name}")
