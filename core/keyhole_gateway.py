"""
KeyholeGateway — ZQ Cognitive Overlay System™
Priority 3 Component: Enterprise AI Trust Plane

Contract Reference: docs/RUNTIME_CONTRACT_v1.md Section 5 (bdad753)
Compliance Reference: docs/CONTRACT_COMPLIANCE.md Part 1.2 (b84b348)

This is the EXCLUSIVE interface between:
  - Execution runtime (Taskmaster)
  - Provider access (LLMs, APIs, tools)
  - Credential storage (Keybox)

Rules:
  - Providers CANNOT bypass this gateway. EVER.
  - All credential access logged as CREDENTIAL_ACCESSED events
  - Permission policy validated BEFORE credential fetch
  - Circuit breaker: 3 consecutive failures = OFFLINE
  - Routing overhead target: < 50ms
  - Provider bypass attempt = P0 incident

Author: Zubin Qayam, ZQ AI LOGIC™
Version: 0.1.0 (skeleton)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from event_appender import EventAppender, EventType, ZQCoreEvent


# ---------------------------------------------------------------------------
# Provider Status
# ---------------------------------------------------------------------------

class ProviderStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


# ---------------------------------------------------------------------------
# Provider Request / Response
# ---------------------------------------------------------------------------

@dataclass
class ProviderRequest:
    provider_id: str
    scope: str                          # Permission scope (e.g. "read", "write")
    payload: dict[str, Any]
    correlation_id: str
    workspace_id: str
    session_id: str
    user_id: Optional[str] = None
    causation_id: Optional[str] = None


@dataclass
class ProviderResponse:
    provider_id: str
    success: bool
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    event_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

@dataclass
class CircuitBreaker:
    """
    Contract: 3 consecutive failures = OFFLINE.
    Provider must be explicitly reset to resume.
    """
    provider_id: str
    max_failures: int = 3
    failure_count: int = 0
    status: ProviderStatus = ProviderStatus.HEALTHY
    last_failure_at: Optional[str] = None

    def record_success(self) -> None:
        self.failure_count = 0
        self.status = ProviderStatus.HEALTHY

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_at = datetime.now(timezone.utc).isoformat()
        if self.failure_count >= self.max_failures:
            self.status = ProviderStatus.OFFLINE
        elif self.failure_count >= 2:
            self.status = ProviderStatus.DEGRADED

    def is_available(self) -> bool:
        return self.status != ProviderStatus.OFFLINE

    def reset(self) -> None:
        """Explicit reset only. No auto-recovery per contract."""
        self.failure_count = 0
        self.status = ProviderStatus.HEALTHY
        self.last_failure_at = None


# ---------------------------------------------------------------------------
# KeyholeGateway
# ---------------------------------------------------------------------------

class KeyholeGateway:
    """
    Enterprise AI Trust Plane.

    CONTRACT:
    - Single entry point for ALL provider requests
    - Permission policy validated before credential fetch
    - All actions logged via EventAppender
    - Circuit breaker enforced
    - NO direct provider bypass tolerated
    """

    def __init__(
        self,
        event_appender: EventAppender,
        keybox: "KeyboxInterface",
        policy_engine: "PolicyEngineInterface",
    ) -> None:
        self._appender = event_appender
        self._keybox = keybox
        self._policy = policy_engine
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._providers: dict[str, "ProviderInterface"] = {}

    # ------------------------------------------------------------------
    # Provider Registration
    # ------------------------------------------------------------------

    def register_provider(
        self,
        provider_id: str,
        provider: "ProviderInterface",
    ) -> None:
        """Register a provider. All providers MUST be registered here."""
        self._providers[provider_id] = provider
        self._circuit_breakers[provider_id] = CircuitBreaker(
            provider_id=provider_id
        )

    # ------------------------------------------------------------------
    # Primary Execution Path (< 50ms target)
    # ------------------------------------------------------------------

    async def request(
        self,
        req: ProviderRequest,
    ) -> ProviderResponse:
        """
        Route a provider request through the trust plane.

        6-step contract flow:
        1. Validate permission policy
        2. Check circuit breaker
        3. Fetch credential from Keybox
        4. Execute provider
        5. Log PROVIDER_EXECUTED event
        6. Return response
        """
        start = time.monotonic()

        # Step 1: Log PROVIDER_REQUESTED (async — non-blocking)
        self._log_async(EventType.PROVIDER_REQUESTED, req, {})

        # Step 2: Validate permission policy
        try:
            self._policy.validate(
                provider_id=req.provider_id,
                scope=req.scope,
                user_id=req.user_id,
                workspace_id=req.workspace_id,
            )
        except PermissionDeniedError as e:
            self._log_async(EventType.POLICY_VIOLATED, req, {"reason": str(e)})
            return ProviderResponse(
                provider_id=req.provider_id,
                success=False,
                error=f"Permission denied: {e}",
            )

        # Step 3: Check circuit breaker
        cb = self._get_circuit_breaker(req.provider_id)
        if not cb.is_available():
            return await self._handle_provider_offline(
                req=req,
                cb=cb,
                latency_ms=(time.monotonic() - start) * 1000,
            )

        # Step 4: Fetch credential (from Keybox only)
        try:
            credential = self._keybox.fetch(
                provider_id=req.provider_id,
                scope=req.scope,
            )
            # Log credential access (async)
            self._log_async(
                EventType.CREDENTIAL_ACCESSED,
                req,
                {"provider_id": req.provider_id, "scope": req.scope},
            )
        except CredentialNotFoundError as e:
            return ProviderResponse(
                provider_id=req.provider_id,
                success=False,
                error=f"Credential not found: {e}",
            )

        # Step 5: Execute provider
        provider = self._providers.get(req.provider_id)
        if not provider:
            return ProviderResponse(
                provider_id=req.provider_id,
                success=False,
                error=f"Provider not registered: {req.provider_id}",
            )

        try:
            result = await provider.execute(
                payload=req.payload,
                credential=credential,
            )
            cb.record_success()
            latency_ms = (time.monotonic() - start) * 1000

            # Step 6: Log PROVIDER_EXECUTED (async)
            event_id = self._log_async(
                EventType.PROVIDER_EXECUTED,
                req,
                {"provider_id": req.provider_id, "latency_ms": latency_ms},
            )

            return ProviderResponse(
                provider_id=req.provider_id,
                success=True,
                result=result,
                latency_ms=latency_ms,
                event_id=event_id,
            )

        except Exception as exc:
            cb.record_failure()
            latency_ms = (time.monotonic() - start) * 1000
            self._log_async(
                EventType.PROVIDER_FAILED,
                req,
                {"provider_id": req.provider_id, "error": str(exc)},
            )

            if not cb.is_available():
                # Circuit opened — provider is now OFFLINE
                return await self._handle_provider_offline(
                    req=req, cb=cb, latency_ms=latency_ms
                )

            return ProviderResponse(
                provider_id=req.provider_id,
                success=False,
                error=str(exc),
                latency_ms=latency_ms,
            )

    # ------------------------------------------------------------------
    # Failover
    # ------------------------------------------------------------------

    async def _handle_provider_offline(
        self,
        req: ProviderRequest,
        cb: CircuitBreaker,
        latency_ms: float,
    ) -> ProviderResponse:
        """
        Contract: escalate to human review when primary is OFFLINE.
        TODO: Implement secondary provider fallback in Phase 2.
        """
        self._log_async(
            EventType.PROVIDER_FAILED,
            req,
            {
                "provider_id": req.provider_id,
                "reason": "circuit_breaker_open",
                "failure_count": cb.failure_count,
            },
        )
        # TODO: Escalate to human review queue
        return ProviderResponse(
            provider_id=req.provider_id,
            success=False,
            error=f"Provider {req.provider_id} is OFFLINE (circuit open). Human escalation required.",
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    # Async Logging (non-blocking side channel)
    # ------------------------------------------------------------------

    def _log_async(
        self,
        event_type: EventType,
        req: ProviderRequest,
        extra_payload: dict[str, Any],
    ) -> str:
        """
        Log to EventAppender as async side channel.
        MUST NOT block the critical path.
        Contract: enqueue < 5ms.
        """
        # TODO: In Phase 2, use asyncio.create_task() or thread pool
        # For now, synchronous best-effort (acceptable for skeleton)
        try:
            event = ZQCoreEvent(
                event_type=event_type,
                source="keyhole",
                correlation_id=req.correlation_id,
                causation_id=req.causation_id,
                payload={"provider_id": req.provider_id, **extra_payload},
                workspace_id=req.workspace_id,
                session_id=req.session_id,
                user_id=req.user_id,
            )
            return self._appender.append(event)
        except Exception:
            # Logging failure MUST NOT break execution
            return ""

    def _get_circuit_breaker(self, provider_id: str) -> CircuitBreaker:
        if provider_id not in self._circuit_breakers:
            self._circuit_breakers[provider_id] = CircuitBreaker(
                provider_id=provider_id
            )
        return self._circuit_breakers[provider_id]


# ---------------------------------------------------------------------------
# Interfaces (to be implemented by Keybox and Providers)
# ---------------------------------------------------------------------------

class KeyboxInterface:
    """Interface for credential vault. Implemented by ZQ_KEYBOX."""

    def fetch(self, provider_id: str, scope: str) -> dict[str, Any]:
        raise NotImplementedError


class PolicyEngineInterface:
    """Interface for permission policy engine."""

    def validate(
        self,
        provider_id: str,
        scope: str,
        user_id: Optional[str],
        workspace_id: str,
    ) -> None:
        """Raise PermissionDeniedError if not allowed."""
        raise NotImplementedError


class ProviderInterface:
    """Interface for provider execution. All LLMs/APIs implement this."""

    async def execute(
        self,
        payload: dict[str, Any],
        credential: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PermissionDeniedError(Exception):
    """Raised when policy engine denies provider access."""


class CredentialNotFoundError(Exception):
    """Raised when Keybox cannot find a credential."""


class ProviderBypassAttemptError(Exception):
    """P0: Raised when bypass of Keyhole is detected."""


# ---------------------------------------------------------------------------
# TODO: Next Steps for this module
# ---------------------------------------------------------------------------
# [ ] Implement true async logging (asyncio.create_task, no blocking)
# [ ] Implement secondary provider fallback registry
# [ ] Implement human escalation queue integration
# [ ] Add latency enforcement (alert if > 50ms)
# [ ] Add provider health monitoring (availability, rate limits, p95)
# [ ] Wire to ZQ_KEYBOX for real credential fetching
# [ ] Implement full PolicyEngine with workspace + user + scope rules
# [ ] Add circuit breaker reset endpoint (manual only, per contract)
# [ ] Tests: keyhole_bypass detection, circuit_breaker_open,
#            credential_access_logged (see CONTRACT_COMPLIANCE.md Part 1.2)
