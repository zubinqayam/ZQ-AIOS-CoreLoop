from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class EventItem(BaseModel):
    event_id: str
    trace_id: str
    seq: int = Field(..., ge=0)
    type: str
    ts: float
    payload: Dict[str, Any]
    version: str = "v1"
    risk_score: Optional[float] = 0.0
    status: Optional[str] = "ok"
