from collections import deque
from typing import Any, Deque, Dict, Optional

EVENT_QUEUE: Deque[Dict[str, Any]] = deque()

def publish(event: Dict[str, Any]) -> None:
    EVENT_QUEUE.append(event)

def consume() -> Optional[Dict[str, Any]]:
    if EVENT_QUEUE:
        return EVENT_QUEUE.popleft()
    return None
