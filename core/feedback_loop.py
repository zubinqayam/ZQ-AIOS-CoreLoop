import time
from typing import Dict, Any, List

from core.global_memory import store_decision, record_failure
from core.agent_memory import record_outcome
from core.multi_agent_consensus import CONSENSUS

# Closed Feedback Loop Engine

class FeedbackLoop:

    def __init__(self):
        pass

    def process_final_outcome(
        self,
        trace_id: str,
        agent_outputs: List[Dict[str, Any]],
        final_decision: str,
        confidence: float,
        publish,
        create_event,
        SRC_SYSTEM
    ):
        """
        Core closed-loop feedback:
        - store decision
        - update agent learning
        - detect failures
        - emit feedback events
        """

        # -------------------------
        # 1. Store global decision
        # -------------------------
        decision_data = {
            "decision": final_decision,
            "confidence": confidence,
            "ts": time.time(),
            "agents": agent_outputs
        }

        store_decision(trace_id, decision_data)

        # -------------------------
        # 2. Evaluate correctness (heuristic for now)
        # -------------------------
        # NOTE: Replace with real ground-truth when available
        correct = confidence >= 0.6

        # -------------------------
        # 3. Update agent learning
        # -------------------------
        for agent in agent_outputs:
            name = agent.get("agent")
            decision = agent.get("decision")

            is_correct = (decision == final_decision) and correct
            record_outcome(name, is_correct)

        # -------------------------
        # 4. Failure detection
        # -------------------------
        if not correct:
            pattern = record_failure(
                {"payload": {"agents": agent_outputs, "decision": final_decision}},
                reason="low_confidence_or_incorrect"
            )

            publish(create_event(
                "system.failure_pattern",
                {
                    "trace_id": trace_id,
                    "pattern_hash": pattern,
                    "confidence": confidence
                },
                SRC_SYSTEM,
                trace_id=trace_id
            ))

        # -------------------------
        # 5. Emit learning event
        # -------------------------
        publish(create_event(
            "system.learning_update",
            {
                "trace_id": trace_id,
                "confidence": confidence,
                "correct": correct
            },
            SRC_SYSTEM,
            trace_id=trace_id
        ))


FEEDBACK = FeedbackLoop()
