from core.schemas import create_event
from core.event_bus import publish, consume
from core.memory import store_event
from core.handlers import EVENT_HANDLERS

SRC_USER = {"service": "user", "instance": "local"}

def run_once():
    task_event = create_event(
        "task.created",
        {"input": "Analyze business opportunity"},
        SRC_USER,
    )
    publish(task_event)

    processed_events = set()

    while True:
        event = consume()
        if not event:
            break

        event_id = event.get("event_id")
        if event_id in processed_events:
            continue
        processed_events.add(event_id)

        store_event(event)

        handler = EVENT_HANDLERS.get(event["type"])
        if handler:
            handler(event, publish)

        if event["type"] in ("system.decision", "system.blocked"):
            print(f"[{event['type']}] trace_id={event['trace_id']} payload={event['payload']}")

if __name__ == "__main__":
    run_once()
