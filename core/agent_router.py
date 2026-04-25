from typing import List, Dict, Any
from core.agent_memory import get_weight

# Agent Registry (expandable)
AGENTS = {
    "planner": {"type": "analysis"},
    "critic": {"type": "validation"},
    "executor": {"type": "execution"},
}

class AgentRouter:

    def __init__(self):
        pass

    def route(self, task_payload: Dict[str, Any]) -> List[str]:
        """
        Select agents dynamically based on task + specialization + performance
        """
        task_type = self._infer_task_type(task_payload)

        scored_agents = []

        for agent, meta in AGENTS.items():
            base_score = 1.0 if meta["type"] == task_type else 0.5
            performance_weight = get_weight(agent)

            final_score = base_score * performance_weight

            scored_agents.append((agent, final_score))

        # sort by score descending
        scored_agents.sort(key=lambda x: x[1], reverse=True)

        # pick top 2–3 agents
        selected = [a[0] for a in scored_agents[:3]]

        return selected

    def _infer_task_type(self, task_payload: Dict[str, Any]) -> str:
        text = task_payload.get("input", "").lower()

        if "analyze" in text or "research" in text:
            return "analysis"
        elif "validate" in text or "check" in text:
            return "validation"
        elif "execute" in text or "build" in text:
            return "execution"

        return "analysis"

ROUTER = AgentRouter()
