from fastapi import APIRouter
import redis
import json

router = APIRouter()
r = redis.Redis(decode_responses=True)
STREAM = "zq.events"

@router.get("/trace/{trace_id}")
def get_trace(trace_id: str):
    results = r.xrange(STREAM, min='-', max='+')
    trace_events = []

    for _, fields in results:
        raw = fields.get("event")
        if not raw:
            continue
        evt = json.loads(raw)
        if evt.get("trace_id") == trace_id:
            trace_events.append(evt)

    return trace_events
