from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
import json
import time
import redis
from typing import List, Dict, Any

REDIS_URL = "redis://localhost:6379/0"
STREAM = "zq.events"

app = FastAPI(title="ZQ Control Room Bridge")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _decode(entries):
    out = []
    for _id, fields in entries:
        raw = fields.get("event")
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


@app.get("/events")
def get_events(limit: int = Query(200, ge=1, le=1000)) -> List[Dict[str, Any]]:
    # Read latest N events
    entries = r.xrevrange(STREAM, max='+', min='-', count=limit)
    events = _decode(entries)
    # return in chronological order
    return list(reversed(events))


def event_stream():
    last_id = '$'
    while True:
        resp = r.xread({STREAM: last_id}, block=2000, count=50)
        if not resp:
            yield 'event: ping\n\n'
            continue
        stream, messages = resp[0]
        for msg_id, fields in messages:
            last_id = msg_id
            raw = fields.get("event")
            if not raw:
                continue
            yield f"data: {raw}\n\n"


@app.get("/events/stream")
def stream_events():
    return StreamingResponse(event_stream(), media_type="text/event-stream")
