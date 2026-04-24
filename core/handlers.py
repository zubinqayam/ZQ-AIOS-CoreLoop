from core.schemas import create_event
from core.agent import process_task
from core.alga import validate

SRC_AGENT  = {"service": "agent",  "instance": "local"}
SRC_ALGA   = {"service": "alga",   "instance": "local"}
SRC_SYSTEM = {"service": "system", "instance": "local"}

def handle_task_created(event, publish):
    result = process_task(event["payload"])
    publish(create_event(
        "agent.response",
        result,
        SRC_AGENT,
        trace_id=event["trace_id"],
    ))

def handle_agent_response(event, publish):
    validation = validate(event["payload"])
    publish(create_event(
        "alga.validation",
        validation,
        SRC_ALGA,
        trace_id=event["trace_id"],
    ))

def handle_alga_validation(event, publish):
    action = event["payload"].get("action")

    if action == "approve":
        publish(create_event(
            "system.decision",
            {"message": "Approved"},
            SRC_SYSTEM,
            trace_id=event["trace_id"],
        ))

    elif action == "retry":
        publish(create_event(
            "system.blocked",
            {
                "message": "Retry requested",
                "reason": event["payload"].get("reason")
            },
            SRC_SYSTEM,
            trace_id=event["trace_id"],
        ))

    else:
        publish(create_event(
            "system.blocked",
            {
                "message": "Rejected",
                "reason": event["payload"].get("reason")
            },
            SRC_SYSTEM,
            trace_id=event["trace_id"],
        ))

EVENT_HANDLERS = {
    "task.created": handle_task_created,
    "agent.response": handle_agent_response,
    "alga.validation": handle_alga_validation,
}
