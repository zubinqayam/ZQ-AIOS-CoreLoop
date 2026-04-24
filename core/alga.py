from typing import Any, Dict

def validate(agent_output: Dict[str, Any]) -> Dict[str, Any]:
    confidence = float(agent_output.get("confidence", 0.0))

    if confidence < 0.5:
        return {
            "status": "failed",
            "risk_score": 0.7,
            "confidence": confidence,
            "action": "retry",
            "reason": "Low confidence",
        }

    return {
        "status": "passed",
        "risk_score": 0.1,
        "confidence": confidence,
        "action": "approve",
    }
