"""
ReplayEngine — ZQ Cognitive Overlay System™
Priority 2 Component: Deterministic Event Replay

Contract Reference: docs/RUNTIME_CONTRACT_v1.md Section 6 (bdad753)
Compliance Reference: docs/CONTRACT_COMPLIANCE.md Part 2 (b84b348)

CRITICAL: Must be built BEFORE overlays, agents, or federation.

Rules:
  - Verify HMAC signature on EVERY event before processing
  - Deterministic: same input sequence = identical output state
  - Simulation Mode: NO external API calls, NO DB writes, NO credential access
  - Supports: Point-in-Time, Causal Chain, Simulation, Audit modes
  - Generates audit report on completion
  - Replay non-determinism = P0 incident

Author: Zubin Qayam, ZQ AI LOGIC™
Version: 0.1.0 (skeleton)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Generator, Optional

from event_appender import EventType, ZQCoreEvent


# ---------------------------------------------------------------------------
# Replay Modes
# ---------------------------------------------------------------------------

class ReplayMode(str, Enum):
    POINT_IN_TIME = "POINT_IN_TIME"    # Reconstruct state at timestamp T
    CAUSAL_CHAIN = "CAUSAL_CHAIN"      # Replay from correlation_id
    SIMULATION = "SIMULATION"          # No side effects
    AUDIT = "AUDIT"                    # Full validation + audit report


# ---------------------------------------------------------------------------
# Replay Result
# ---------------------------------------------------------------------------

@dataclass
class ReplayResult:
    mode: ReplayMode
    events_processed: int
    events_skipped: int
    integrity_failures: int
    final_state: dict[str, Any]
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    started_at: str = ""
    completed_at: str = ""


# ---------------------------------------------------------------------------
# EventRecord (raw row from WAL)
# ---------------------------------------------------------------------------

@dataclass
class EventRecord:
    event_id: str
    event_type: str
    timestamp: str
    source: str
    correlation_id: str
    causation_id: Optional[str]
    workspace_id: str
    session_id: str
    user_id: Optional[str]
    version: str
    payload: dict[str, Any]
    signature: str


# ---------------------------------------------------------------------------
# ReplayEngine
# ---------------------------------------------------------------------------

class ReplayEngine:
    """
    Deterministic event replay engine.

    CONTRACT:
    - All HMAC signatures verified before processing
    - Simulation mode produces zero side effects
    - Identical event sequence MUST produce identical output state
    """

    def __init__(self, db_path: str, hmac_secret: bytes) -> None:
        self._db_path = db_path
        self._hmac_secret = hmac_secret
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    # ------------------------------------------------------------------
    # Public Replay API
    # ------------------------------------------------------------------

    def replay_to(
        self,
        timestamp: str,
        workspace_id: str,
        mode: ReplayMode = ReplayMode.AUDIT,
    ) -> ReplayResult:
        """
        Point-in-Time Replay: reconstruct state at timestamp T.

        Contract requirement: output state must be identical to
        original state at T given the same event sequence.
        """
        events = list(self._load_events_before(
            timestamp=timestamp,
            workspace_id=workspace_id,
        ))
        return self._execute_replay(
            events=events,
            mode=mode,
            context={"replay_type": "point_in_time", "target_timestamp": timestamp},
        )

    def replay_causal_chain(
        self,
        correlation_id: str,
        mode: ReplayMode = ReplayMode.AUDIT,
    ) -> ReplayResult:
        """
        Causal Chain Replay: replay all events from a correlation_id.
        Child events always processed after parent events.
        """
        events = list(self._load_causal_chain(correlation_id))
        return self._execute_replay(
            events=events,
            mode=mode,
            context={"replay_type": "causal_chain", "correlation_id": correlation_id},
        )

    def replay_simulation(
        self,
        correlation_id: str,
    ) -> ReplayResult:
        """
        Simulation Mode: replay without any side effects.

        CONTRACT:
        - NO external API calls
        - NO database writes
        - NO credential access
        """
        return self.replay_causal_chain(
            correlation_id=correlation_id,
            mode=ReplayMode.SIMULATION,
        )

    # ------------------------------------------------------------------
    # Core Replay Execution
    # ------------------------------------------------------------------

    def _execute_replay(
        self,
        events: list[EventRecord],
        mode: ReplayMode,
        context: dict[str, Any],
    ) -> ReplayResult:
        """Execute replay over an ordered event sequence."""
        result = ReplayResult(
            mode=mode,
            events_processed=0,
            events_skipped=0,
            integrity_failures=0,
            final_state={},
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        state: dict[str, Any] = {}

        for event in events:
            # HMAC verification is MANDATORY before any processing
            if not self._verify_signature(event):
                result.integrity_failures += 1
                result.audit_log.append({
                    "event_id": event.event_id,
                    "status": "INTEGRITY_FAILURE",
                    "reason": "HMAC signature verification failed",
                })
                if mode == ReplayMode.AUDIT:
                    # In audit mode, abort on integrity failure
                    result.success = False
                    result.error = f"Integrity failure on event {event.event_id}"
                    break
                else:
                    result.events_skipped += 1
                    continue

            # Apply event to state
            try:
                self._apply_event(event, state, mode)
                result.events_processed += 1

                if mode == ReplayMode.AUDIT:
                    result.audit_log.append({
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "timestamp": event.timestamp,
                        "source": event.source,
                        "status": "PROCESSED",
                    })
            except SideEffectBlockedError as e:
                # Simulation mode blocked a prohibited side effect
                result.audit_log.append({
                    "event_id": event.event_id,
                    "status": "SIDE_EFFECT_BLOCKED",
                    "reason": str(e),
                })
                result.events_skipped += 1

        result.final_state = state
        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    def _apply_event(
        self,
        event: EventRecord,
        state: dict[str, Any],
        mode: ReplayMode,
    ) -> None:
        """
        Apply a single event to the state machine.

        Simulation mode MUST block any side-effecting operations.
        """
        event_type = event.event_type

        # Simulation mode blocks provider execution and credential access
        if mode == ReplayMode.SIMULATION:
            if event_type in (
                EventType.PROVIDER_EXECUTED.value,
                EventType.CREDENTIAL_ACCESSED.value,
            ):
                raise SideEffectBlockedError(
                    f"Simulation mode blocked side-effecting event: {event_type}"
                )

        # State machine transitions
        # TODO: Expand with full domain state transitions in Phase 2
        if event_type == EventType.TASK_CREATED.value:
            task_id = event.payload.get("task_id", event.event_id)
            state.setdefault("tasks", {})[task_id] = {
                "status": "created",
                "created_at": event.timestamp,
                "payload": event.payload,
            }

        elif event_type == EventType.TASK_COMPLETED.value:
            task_id = event.payload.get("task_id")
            if task_id and task_id in state.get("tasks", {}):
                state["tasks"][task_id]["status"] = "completed"
                state["tasks"][task_id]["completed_at"] = event.timestamp

        elif event_type == EventType.TASK_FAILED.value:
            task_id = event.payload.get("task_id")
            if task_id and task_id in state.get("tasks", {}):
                state["tasks"][task_id]["status"] = "failed"
                state["tasks"][task_id]["failed_at"] = event.timestamp
                state["tasks"][task_id]["error"] = event.payload.get("error")

        elif event_type == EventType.PROVIDER_EXECUTED.value:
            state.setdefault("provider_calls", []).append({
                "provider": event.payload.get("provider_id"),
                "timestamp": event.timestamp,
                "source": event.source,
            })

        # Record every event in the audit trail
        state.setdefault("event_sequence", []).append(event.event_id)

    # ------------------------------------------------------------------
    # HMAC Verification (contract: mandatory before processing)
    # ------------------------------------------------------------------

    def _verify_signature(self, event: EventRecord) -> bool:
        """Verify HMAC-SHA256 signature. Contract requirement."""
        message = (
            f"{event.event_id}:{event.event_type}:{event.correlation_id}"
        )
        expected = hmac.new(
            self._hmac_secret,
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, event.signature)

    # ------------------------------------------------------------------
    # WAL Queries (read-only)
    # ------------------------------------------------------------------

    def _load_events_before(
        self,
        timestamp: str,
        workspace_id: str,
    ) -> Generator[EventRecord, None, None]:
        """Load events up to (and including) a timestamp in causal order."""
        cursor = self._conn.execute(
            """
            SELECT * FROM events
            WHERE workspace_id = ?
              AND timestamp <= ?
            ORDER BY id ASC
            """,
            (workspace_id, timestamp),
        )
        for row in cursor:
            yield self._row_to_record(row)

    def _load_causal_chain(
        self,
        correlation_id: str,
    ) -> Generator[EventRecord, None, None]:
        """Load all events in a causal chain, ordered by id (insertion order)."""
        cursor = self._conn.execute(
            """
            SELECT * FROM events
            WHERE correlation_id = ?
            ORDER BY id ASC
            """,
            (correlation_id,),
        )
        for row in cursor:
            yield self._row_to_record(row)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> EventRecord:
        return EventRecord(
            event_id=row["event_id"],
            event_type=row["event_type"],
            timestamp=row["timestamp"],
            source=row["source"],
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            workspace_id=row["workspace_id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            version=row["version"],
            payload=json.loads(row["payload"]),
            signature=row["signature"],
        )

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ReplayIntegrityError(Exception):
    """Raised when HMAC verification fails during replay."""


class SideEffectBlockedError(Exception):
    """Raised in Simulation mode when a side-effecting event is blocked."""


# ---------------------------------------------------------------------------
# TODO: Next Steps for this module
# ---------------------------------------------------------------------------
# [ ] Implement full domain state machine (all EventType transitions)
# [ ] Add Lamport clock ordering verification
# [ ] Add snapshot-based fast-forward (skip to nearest snapshot, then replay delta)
# [ ] Add audit report export (JSON + human-readable)
# [ ] Add replay_determinism test harness (run twice, compare states)
# [ ] Wire MEMORY_REPLAY_STARTED / COMPLETED events to EventAppender
# [ ] Add enterprise NATS event source (Phase 2 federation)
# [ ] Tests: replay_determinism, replay_causal_ordering,
#            replay_integrity, replay_simulation_isolation,
#            replay_point_in_time (see CONTRACT_COMPLIANCE.md Part 2)
