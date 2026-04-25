import random
from typing import List, Dict, Any
from core.agent_memory import get_weight

# Exploration vs Exploitation Engine (Epsilon-Greedy)

EPSILON = 0.2  # 20% exploration

class ExplorationEngine:

    def __init__(self):
        pass

    def select_agents(self, scored_agents: List[tuple]) -> List[str]:
        """
        scored_agents: [(agent, score)]
        """
        if random.random() < EPSILON:
            # Exploration: random agents
            return self._explore(scored_agents)
        else:
            # Exploitation: best agents
            return self._exploit(scored_agents)

    def _explore(self, scored_agents):
        agents = [a[0] for a in scored_agents]
        return random.sample(agents, min(3, len(agents)))

    def _exploit(self, scored_agents):
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        return [a[0] for a in scored_agents[:3]]

    def update_epsilon(self, performance_delta: float):
        global EPSILON

        # If system improving → reduce exploration
        if performance_delta > 0:
            EPSILON = max(0.05, EPSILON - 0.01)
        else:
            EPSILON = min(0.5, EPSILON + 0.02)

EXPLORER = ExplorationEngine()
