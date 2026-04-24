from typing import Any, Dict

def process_task(task_payload: Dict[str, Any]) -> Dict[str, Any]:
    text = task_payload["input"]
    return {
        "decision": f"Processed: {text}",
        "confidence": 0.8,
    }
