import uuid
import time
from typing import Any, Dict, Optional

def create_event(
    event_type: str,
    payload: Dict[str, Any],
    source: Dict[str, str],
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "event_id": str(uuid.uuid4()),
        "type": event_type,
        "ts": time.time(),
        "trace_id": trace_id or str(uuid.uuid4()),
        "source": source,
        "payload": payload,
    }
