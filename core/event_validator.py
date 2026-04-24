from core.event_schema import EventItem


def validate_event(event: dict) -> dict:
    validated = EventItem(**event)
    return validated.model_dump()
