import json
import os
from typing import Any, Dict

MEMORY_PATH = os.path.join("data", "memory.jsonl")

def store_event(event: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
