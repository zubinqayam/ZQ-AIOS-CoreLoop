import redis
import json
import hashlib
from typing import Dict, Any

r = redis.Redis(decode_responses=True)

# -----------------------------
# GLOBAL DECISION MEMORY
# -----------------------------

def store_decision(trace_id: str, decision_data: Dict[str, Any]):
    """
    Stores final decision outcome for a trace
    """
    key = f"trace:{trace_id}:final"
    r.set(key, json.dumps(decision_data))


def get_decision(trace_id: str):
    data = r.get(f"trace:{trace_id}:final")
    return json.loads(data) if data else None


# -----------------------------
# FAILURE INTELLIGENCE SYSTEM
# -----------------------------

def _hash_failure(payload: Dict[str, Any]) -> str:
    """
    Generate a pattern hash for failure clustering
    """
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def record_failure(event: Dict[str, Any], reason: str):
    """
    Store failure pattern and increment occurrence
    """
    pattern_hash = _hash_failure(event.get("payload", {}))

    key = f"failure:{pattern_hash}"

    existing = r.get(key)
    if existing:
        data = json.loads(existing)
    else:
        data = {
            "count": 0,
            "reason": reason,
            "sample": event.get("payload", {})
        }

    data["count"] += 1

    r.set(key, json.dumps(data))

    return pattern_hash


def get_failure_pattern(pattern_hash: str):
    data = r.get(f"failure:{pattern_hash}")
    return json.loads(data) if data else None


# -----------------------------
# FAILURE HOTSPOT DETECTION
# -----------------------------

def get_top_failures(limit: int = 10):
    keys = r.keys("failure:*")

    failures = []
    for k in keys:
        data = json.loads(r.get(k))
        failures.append((k, data))

    failures.sort(key=lambda x: x[1]["count"], reverse=True)

    return failures[:limit]
