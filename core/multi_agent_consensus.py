from typing import List, Dict, Any
import statistics

# Simple multi-agent consensus engine

class ConsensusEngine:
    def __init__(self):
        pass

    def evaluate(self, agent_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        agent_outputs = [
            {"agent": "A", "decision": "approve", "confidence": 0.8},
            {"agent": "B", "decision": "approve", "confidence": 0.6},
            {"agent": "C", "decision": "reject", "confidence": 0.7},
        ]
        """

        decisions = [a["decision"] for a in agent_outputs]
        confidences = [a.get("confidence", 0.0) for a in agent_outputs]

        # Majority decision
        decision = max(set(decisions), key=decisions.count)

        # Confidence aggregation
        avg_conf = statistics.mean(confidences) if confidences else 0.0

        # Disagreement detection
        disagreement = len(set(decisions)) > 1

        return {
            "final_decision": decision,
            "confidence": avg_conf,
            "disagreement": disagreement,
            "agents": agent_outputs
        }

CONSENSUS = ConsensusEngine()
