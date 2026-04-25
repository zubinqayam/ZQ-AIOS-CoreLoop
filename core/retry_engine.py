from typing import Dict, Any
import time

# Autonomous Retry + Self-Healing Engine

MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

class RetryEngine:

    def __init__(self):
        self.retry_tracker = {}  # trace_id -> count

    def should_retry(self, trace_id: str, action: str, confidence: float) -> bool:
        count = self.retry_tracker.get(trace_id, 0)

        if count >= MAX_RETRIES:
            return False

        if action in ("retry", "escalate") or confidence < 0.5:
            return True

        return False

    def register_retry(self, trace_id: str):
        self.retry_tracker[trace_id] = self.retry_tracker.get(trace_id, 0) + 1

    def reset(self, trace_id: str):
        if trace_id in self.retry_tracker:
            del self.retry_tracker[trace_id]

    def execute_retry(self, trace_id: str, task_payload: Dict[str, Any], publish, create_event, SRC_SYSTEM):
        self.register_retry(trace_id)

        time.sleep(RETRY_DELAY)

        publish(create_event(
            "task.retry",
            {
                "original_task": task_payload,
                "retry_count": self.retry_tracker[trace_id]
            },
            SRC_SYSTEM,
            trace_id=trace_id
        ))

RETRY_ENGINE = RetryEngine()
