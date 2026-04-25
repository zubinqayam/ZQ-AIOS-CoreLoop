import json
from typing import List, Dict, Any
from core.alga_supreme import SUPREME

# Replay + Simulation Engine

class ReplaySimulation:

    def __init__(self):
        pass

    def load_events(self, file_path: str) -> List[Dict[str, Any]]:
        events = []
        with open(file_path, "r") as f:
            for line in f:
                events.append(json.loads(line))
        return events

    def replay(self, events: List[Dict[str, Any]]):
        results = []

        for event in events:
            if event.get("type") == "alga.validation":
                gov_event = SUPREME.evaluate(event)

                results.append({
                    "trace_id": event.get("trace_id"),
                    "original": event.get("payload"),
                    "governance": gov_event["payload"]
                })

        return results

    def compare(self, replay_results: List[Dict[str, Any]]):
        summary = {
            "total": len(replay_results),
            "approved": 0,
            "blocked": 0,
            "review": 0,
            "retry": 0
        }

        for r in replay_results:
            decision = r["governance"]["final_decision"]

            if decision in summary:
                summary[decision] += 1

        return summary


SIMULATOR = ReplaySimulation()
