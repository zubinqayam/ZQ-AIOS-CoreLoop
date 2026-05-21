"""
EventAppender — ZQ Cognitive Overlay System™
Priority 1 Component: Immutable WAL Event Persistence

Contract Reference: docs/RUNTIME_CONTRACT_v1.md (bdad753)
Compliance Reference: docs/CONTRACT_COMPLIANCE.md (b84b348)

Rules:
  - Append-only. No UPDATE. No DELETE. Ever.
  - SHA256 event_id = SHA256(timestamp + source + type + nonce)
  - HMAC-SHA256 signature on every event before write
  - Duplicate detection via event_id check before insert
  - Target write latency: < 10ms under normal load
  - Emits VALIDATION_FAILED governance event on schema violation

Author: Zubin Qayam, ZQ AI LOGIC™
Version: 0.1.0 (skeleton)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Event Types (extend as defined in RUNTIME_CONTRACT_v1.md Section 2.2)
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    # Orchestration
    TASK_CREATED = "TASK_CREATED"
    TASK_DISPATCHED = "TASK_DISPATCHED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_CANCELLED = "TASK_CANCELLED"

    # Provider
    PROVIDER_REQUESTED = "PROVIDER_REQUESTED"
    PROVIDER_AUTHORIZED = "PROVIDER_AUTHORIZED"
    PROVIDER_EXECUTED = "PROVIDER_EXECUTED"
    PROVIDER_FAILED = "PROVIDER_FAILED"
    CREDENTIAL_ACCESSED = "CREDENTIAL_ACCESSED"

    # Governance
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_PASSED = "VALIDATION_PASSED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    POLICY_VIOLATED = "POLICY_VIOLATED"

    # Memory
    MEMORY_SNAPSHOT_CREATED = "MEMORY_SNAPSHOT_CREATED"
    MEMORY_REPLAY_STARTED = "MEMORY_REPLAY_STARTED"
    MEMORY_REPLAY_COMPLETED = "MEMORY_REPLAY_COMPLETED"

    # System
    ASYNC_BOUNDARY_VIOLATION = "ASYNC_BOUNDARY_VIOLATION"


# ---------------------------------------------------------------------------
# Event Dataclass
# ---------------------------------------------------------------------------

@dataclass
class ZQCoreEvent:
    event_type: EventType
    source: str                          # Component ID (taskmaster, keyhole, etc.)
    correlation_id: str                  # End-to-end trace ID
    payload: dict[str, Any]
    workspace_id: str
    session_id: str
    causation_id: Optional[str] = None  # Parent event ID for causal chains
    user_id: Optional[str] = None
    version: str = "1.0.0"

    # Computed on append (do not set manually)
    event_id: str = field(default="", init=False)
    timestamp: str = field(default="", init=False)
    signature: str = field(default="", init=False)


# ---------------------------------------------------------------------------
# EventAppender
# ---------------------------------------------------------------------------

class EventAppender:
    """
    Immutable WAL event appender.

    CONTRACT: This class MUST only ever INSERT to the events table.
    Any attempt to UPDATE or DELETE is a P0 contract violation.
    """

    WAL_SCHEMA = """
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id    TEXT NOT NULL UNIQUE,
            event_type  TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            source      TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            causation_id   TEXT,
            workspace_id   TEXT NOT NULL,
            session_id     TEXT NOT NULL,
            user_id        TEXT,
            version        TEXT NOT NULL,
            payload        TEXT NOT NULL,
            signature      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_correlation ON events(correlation_id);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type);
    """

    def __init__(self, db_path: str, hmac_secret: bytes) -> None:
        """
        Args:
            db_path: Path to SQLite WAL database file.
            hmac_secret: Secret key for HMAC-SHA256 signing.
        """
        self._db_path = db_path
        self._hmac_secret = hmac_secret
        self._conn = self._init_db()

    def _init_db(self) -> sqlite3.Connection:
        """Initialize SQLite in WAL mode. Contract requirement."""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -64000;")  # 64MB
        conn.executescript(self.WAL_SCHEMA)
        conn.commit()
        return conn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append(self, event: ZQCoreEvent) -> str:
        """
        Append an event to the immutable WAL.

        Returns:
            event_id (str) on success.

        Raises:
            EventValidationError: If schema validation fails.
            DuplicateEventError: If event_id already exists.
        """
        self._validate(event)

        nonce = uuid.uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        event_id = self._compute_event_id(
            timestamp=timestamp,
            source=event.source,
            event_type=event.event_type.value,
            nonce=nonce,
        )
        signature = self._compute_signature(event_id, event)

        event.event_id = event_id
        event.timestamp = timestamp
        event.signature = signature

        self._check_duplicate(event_id)
        self._write(event)

        return event_id

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    def _validate(self, event: ZQCoreEvent) -> None:
        """Validate event schema before append."""
        errors = []
        if not event.event_type:
            errors.append("event_type is required")
        if not event.source:
            errors.append("source is required")
        if not event.correlation_id:
            errors.append("correlation_id is required")
        if not event.workspace_id:
            errors.append("workspace_id is required")
        if not event.session_id:
            errors.append("session_id is required")
        if event.payload is None:
            errors.append("payload is required")
        if errors:
            self._emit_validation_failed(event, errors)
            raise EventValidationError(f"Schema validation failed: {errors}")

    @staticmethod
    def _compute_event_id(
        timestamp: str,
        source: str,
        event_type: str,
        nonce: str,
    ) -> str:
        """SHA256(timestamp + source + type + nonce) — contract requirement."""
        raw = f"{timestamp}:{source}:{event_type}:{nonce}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _compute_signature(self, event_id: str, event: ZQCoreEvent) -> str:
        """HMAC-SHA256 signature — contract requirement."""
        message = f"{event_id}:{event.event_type.value}:{event.correlation_id}"
        return hmac.new(
            self._hmac_secret,
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _check_duplicate(self, event_id: str) -> None:
        """Reject duplicate event IDs — contract requirement."""
        cursor = self._conn.execute(
            "SELECT 1 FROM events WHERE event_id = ? LIMIT 1",
            (event_id,),
        )
        if cursor.fetchone():
            raise DuplicateEventError(f"Duplicate event_id: {event_id}")

    def _write(self, event: ZQCoreEvent) -> None:
        """
        INSERT ONLY. No UPDATE. No DELETE. Contract law.
        """
        self._conn.execute(
            """
            INSERT INTO events (
                event_id, event_type, timestamp, source,
                correlation_id, causation_id, workspace_id,
                session_id, user_id, version, payload, signature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.event_type.value,
                event.timestamp,
                event.source,
                event.correlation_id,
                event.causation_id,
                event.workspace_id,
                event.session_id,
                event.user_id,
                event.version,
                json.dumps(event.payload),
                event.signature,
            ),
        )
        self._conn.commit()

    def _emit_validation_failed(self, event: ZQCoreEvent, errors: list[str]) -> None:
        """Best-effort emit of VALIDATION_FAILED governance event."""
        # TODO: Wire to async governance channel in Phase 2
        # For now, log to stderr
        import sys
        print(
            f"[VALIDATION_FAILED] source={event.source} "
            f"correlation={event.correlation_id} errors={errors}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EventValidationError(Exception):
    """Raised when an event fails schema validation."""


class DuplicateEventError(Exception):
    """Raised when a duplicate event_id is detected."""


# ---------------------------------------------------------------------------
# TODO: Next Steps for this module
# ---------------------------------------------------------------------------
# [ ] Wire _emit_validation_failed to async ALGA governance channel
# [ ] Add Lamport logical clock for deterministic ordering
# [ ] Add batch append with atomic transaction
# [ ] Add WAL snapshot/rotation logic (30-day rolling)
# [ ] Add metrics emission (write latency < 10ms enforcement)
# [ ] Add startup WAL integrity check
# [ ] Tests: replay_determinism, wal_corruption_recovery (see CONTRACT_COMPLIANCE.md)
