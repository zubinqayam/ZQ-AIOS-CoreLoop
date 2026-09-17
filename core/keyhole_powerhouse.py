from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Protocol


SENSITIVE_KEYS = {
    "api_key", "apikey", "access_token", "refresh_token", "authorization",
    "password", "secret", "token", "client_secret",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _fingerprint(secret_value: str) -> str:
    digest = hashlib.sha256(secret_value.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


def _mask_account(value: str | None) -> str | None:
    if not value:
        return None
    if "@" in value:
        local, domain = value.split("@", 1)
        return f"{local[:1] or '*'}***@{domain}"
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"


def _redact(value: Any, secret_values: tuple[str, ...] = ()) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in SENSITIVE_KEYS:
                clean[key] = "[REDACTED]"
            else:
                clean[key] = _redact(item, secret_values)
        return clean
    if isinstance(value, list):
        return [_redact(item, secret_values) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item, secret_values) for item in value)
    if isinstance(value, str):
        clean = value
        for secret_value in secret_values:
            if secret_value:
                clean = clean.replace(secret_value, "[REDACTED]")
        return clean
    return value


class ConnectionType(str, Enum):
    API_KEY = "API_KEY"
    OAUTH = "OAUTH"


class LockerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class GrantStatus(str, Enum):
    OPEN = "OPEN"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    EXHAUSTED = "EXHAUSTED"


class KeyholeState(str, Enum):
    LOCKED = "LOCKED"
    READY = "READY"
    OPEN = "OPEN"
    EXPIRING = "EXPIRING"
    REVOKED = "REVOKED"


class SecretStore(Protocol):
    def put(self, value: dict[str, str]) -> str: ...
    def get(self, ref: str) -> dict[str, str]: ...
    def delete(self, ref: str) -> None: ...


class ProviderAdapter(Protocol):
    async def execute(
        self, payload: dict[str, Any], credential: dict[str, str]
    ) -> dict[str, Any]: ...


class InMemorySecretStore:
    """Development/test-only. Production must use an OS keychain, KMS/HSM, or vault."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, str]] = {}

    def put(self, value: dict[str, str]) -> str:
        ref = f"mem:{secrets.token_hex(12)}"
        self._data[ref] = dict(value)
        return ref

    def get(self, ref: str) -> dict[str, str]:
        if ref not in self._data:
            raise KeyError("Secret reference not found")
        return dict(self._data[ref])

    def delete(self, ref: str) -> None:
        self._data.pop(ref, None)


@dataclass
class KeyBoxLocker:
    locker_id: str
    provider: str
    connection_type: ConnectionType
    label: str
    secret_ref: str = field(repr=False)
    secret_fingerprint: str
    allowed_capabilities: tuple[str, ...]
    account_display: str | None = None
    status: LockerStatus = LockerStatus.ACTIVE
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)
    last_used_at: datetime | None = None

    def public_view(self) -> dict[str, Any]:
        return {
            "locker_id": self.locker_id,
            "provider": self.provider,
            "connection_type": self.connection_type.value,
            "label": self.label,
            "account_display": _mask_account(self.account_display),
            "secret_fingerprint": self.secret_fingerprint,
            "allowed_capabilities": list(self.allowed_capabilities),
            "status": self.status.value,
            "expires_at": _iso(self.expires_at),
            "created_at": _iso(self.created_at),
            "last_used_at": _iso(self.last_used_at),
        }


@dataclass
class KeyholeGrant:
    grant_id: str
    locker_id: str
    subject_id: str
    capabilities: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    request_budget: int
    requests_used: int = 0
    status: GrantStatus = GrantStatus.OPEN

    def is_expired(self, now: datetime | None = None) -> bool:
        return (now or _utcnow()) >= self.expires_at


@dataclass
class KeyholeReceipt:
    receipt_id: str
    grant_id: str
    subject_id: str
    task_type: str
    provider: str
    credential_fingerprint: str
    requested_capability: str
    request_hash: str
    response_hash: str | None
    authorization_result: str
    redaction_passed: bool
    created_at: str
    source_urls: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_urls"] = list(self.source_urls)
        return data


class SimpleKeyBox:
    """Small credential registry. Secret material stays behind SecretStore."""

    def __init__(self, secret_store: SecretStore) -> None:
        self._secret_store = secret_store
        self._lockers: dict[str, KeyBoxLocker] = {}

    def connect_api_key(
        self,
        *,
        provider: str,
        label: str,
        api_key: str,
        allowed_capabilities: list[str] | tuple[str, ...],
    ) -> dict[str, Any]:
        if not api_key.strip():
            raise ValueError("api_key cannot be empty")
        return self._connect(
            provider=provider,
            connection_type=ConnectionType.API_KEY,
            label=label,
            credential={"api_key": api_key},
            allowed_capabilities=allowed_capabilities,
        ).public_view()

    def connect_oauth(
        self,
        *,
        provider: str,
        label: str,
        access_token: str,
        allowed_capabilities: list[str] | tuple[str, ...],
        account_display: str | None = None,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        if not access_token.strip():
            raise ValueError("access_token cannot be empty")
        credential = {"access_token": access_token}
        if refresh_token:
            credential["refresh_token"] = refresh_token
        return self._connect(
            provider=provider,
            connection_type=ConnectionType.OAUTH,
            label=label,
            credential=credential,
            allowed_capabilities=allowed_capabilities,
            account_display=account_display,
            expires_at=expires_at,
        ).public_view()

    def _connect(
        self,
        *,
        provider: str,
        connection_type: ConnectionType,
        label: str,
        credential: dict[str, str],
        allowed_capabilities: list[str] | tuple[str, ...],
        account_display: str | None = None,
        expires_at: datetime | None = None,
    ) -> KeyBoxLocker:
        capabilities = tuple(dict.fromkeys(
            cap.strip() for cap in allowed_capabilities if cap.strip()
        ))
        if not capabilities:
            raise ValueError("At least one allowed capability is required")
        primary_secret = credential.get("api_key") or credential.get("access_token") or ""
        secret_ref = self._secret_store.put(credential)
        locker = KeyBoxLocker(
            locker_id=f"kb_{secrets.token_hex(8)}",
            provider=provider.strip().lower(),
            connection_type=connection_type,
            label=label.strip(),
            account_display=account_display,
            secret_ref=secret_ref,
            secret_fingerprint=_fingerprint(primary_secret),
            allowed_capabilities=capabilities,
            expires_at=expires_at,
        )
        self._lockers[locker.locker_id] = locker
        return locker

    def list_lockers(self) -> list[dict[str, Any]]:
        self._refresh_expiry()
        return [locker.public_view() for locker in self._lockers.values()]

    def get_public(self, locker_id: str) -> dict[str, Any]:
        return self._get_locker(locker_id).public_view()

    def disable(self, locker_id: str) -> dict[str, Any]:
        locker = self._get_locker(locker_id)
        locker.status = LockerStatus.DISABLED
        return locker.public_view()

    def revoke(self, locker_id: str) -> dict[str, Any]:
        locker = self._get_locker(locker_id)
        self._secret_store.delete(locker.secret_ref)
        locker.status = LockerStatus.REVOKED
        return locker.public_view()

    def _borrow(
        self, locker_id: str, capability: str
    ) -> tuple[KeyBoxLocker, dict[str, str]]:
        locker = self._get_locker(locker_id)
        self._refresh_one(locker)
        if locker.status != LockerStatus.ACTIVE:
            raise PermissionError(f"Locker is not active: {locker.status.value}")
        if capability not in locker.allowed_capabilities:
            raise PermissionError(f"Locker does not allow capability: {capability}")
        locker.last_used_at = _utcnow()
        return locker, self._secret_store.get(locker.secret_ref)

    def _get_locker(self, locker_id: str) -> KeyBoxLocker:
        if locker_id not in self._lockers:
            raise KeyError(f"Unknown locker: {locker_id}")
        return self._lockers[locker_id]

    def _refresh_expiry(self) -> None:
        for locker in self._lockers.values():
            self._refresh_one(locker)

    @staticmethod
    def _refresh_one(locker: KeyBoxLocker) -> None:
        if (
            locker.status == LockerStatus.ACTIVE
            and locker.expires_at
            and locker.expires_at <= _utcnow()
        ):
            locker.status = LockerStatus.EXPIRED


class KeyholePowerhouse:
    """Simple capability gateway for Search Brain and AutoTechServ read-only use."""

    def __init__(self, keybox: SimpleKeyBox) -> None:
        self._keybox = keybox
        self._providers: dict[str, ProviderAdapter] = {}
        self._grants: dict[str, KeyholeGrant] = {}
        self._receipts: list[KeyholeReceipt] = []

    def register_provider(self, provider: str, adapter: ProviderAdapter) -> None:
        self._providers[provider.strip().lower()] = adapter

    def open(
        self,
        *,
        locker_id: str,
        subject_id: str,
        capabilities: list[str] | tuple[str, ...],
        ttl_seconds: int = 1800,
        request_budget: int = 40,
    ) -> dict[str, Any]:
        if ttl_seconds <= 0 or ttl_seconds > 3600:
            raise ValueError("ttl_seconds must be between 1 and 3600")
        if request_budget <= 0:
            raise ValueError("request_budget must be positive")
        locker = self._keybox._get_locker(locker_id)
        requested = tuple(dict.fromkeys(capabilities))
        if locker.status != LockerStatus.ACTIVE:
            raise PermissionError(f"Locker is not active: {locker.status.value}")
        disallowed = set(requested) - set(locker.allowed_capabilities)
        if disallowed:
            raise PermissionError(
                f"Capability not allowed by locker: {sorted(disallowed)}"
            )
        now = _utcnow()
        grant = KeyholeGrant(
            grant_id=f"khg_{secrets.token_hex(8)}",
            locker_id=locker_id,
            subject_id=subject_id,
            capabilities=requested,
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            request_budget=request_budget,
        )
        self._grants[grant.grant_id] = grant
        return self.grant_status(grant.grant_id)

    def close(self, grant_id: str) -> dict[str, Any]:
        grant = self._get_grant(grant_id)
        grant.status = GrantStatus.REVOKED
        return self.grant_status(grant_id)

    def grant_status(self, grant_id: str) -> dict[str, Any]:
        grant = self._get_grant(grant_id)
        self._refresh_grant(grant)
        return {
            "grant_id": grant.grant_id,
            "locker_id": grant.locker_id,
            "subject_id": grant.subject_id,
            "capabilities": list(grant.capabilities),
            "issued_at": _iso(grant.issued_at),
            "expires_at": _iso(grant.expires_at),
            "request_budget": grant.request_budget,
            "requests_used": grant.requests_used,
            "status": grant.status.value,
        }

    def state(self) -> dict[str, Any]:
        lockers = self._keybox.list_lockers()
        active_lockers = [
            item for item in lockers if item["status"] == LockerStatus.ACTIVE.value
        ]
        open_grants: list[KeyholeGrant] = []
        for grant in self._grants.values():
            self._refresh_grant(grant)
            if grant.status == GrantStatus.OPEN:
                open_grants.append(grant)
        if open_grants:
            soonest = min(g.expires_at for g in open_grants)
            state = (
                KeyholeState.EXPIRING
                if soonest - _utcnow() <= timedelta(minutes=5)
                else KeyholeState.OPEN
            )
        elif active_lockers:
            state = KeyholeState.READY
        elif any(
            item["status"] == LockerStatus.REVOKED.value for item in lockers
        ):
            state = KeyholeState.REVOKED
        else:
            state = KeyholeState.LOCKED
        return {
            "state": state.value,
            "active_lockers": len(active_lockers),
            "open_grants": len(open_grants),
        }

    async def execute(
        self,
        *,
        grant_id: str,
        task_type: str,
        requested_capability: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        grant = self._get_grant(grant_id)
        self._refresh_grant(grant)
        if grant.status != GrantStatus.OPEN:
            return self._denied(
                grant, task_type, requested_capability, payload,
                f"grant_{grant.status.value.lower()}",
            )
        if requested_capability not in grant.capabilities:
            return self._denied(
                grant, task_type, requested_capability, payload,
                "capability_not_in_grant",
            )
        if grant.requests_used >= grant.request_budget:
            grant.status = GrantStatus.EXHAUSTED
            return self._denied(
                grant, task_type, requested_capability, payload,
                "request_budget_exhausted",
            )

        try:
            locker, credential = self._keybox._borrow(
                grant.locker_id, requested_capability
            )
        except (KeyError, PermissionError) as exc:
            return self._denied(
                grant, task_type, requested_capability, payload, str(exc)
            )

        adapter = self._providers.get(locker.provider)
        if adapter is None:
            return self._denied(
                grant, task_type, requested_capability, payload,
                "provider_not_registered",
            )

        grant.requests_used += 1
        request_hash = _digest(_redact(payload))
        raw_result = await adapter.execute(
            payload=dict(payload), credential=credential
        )
        secret_values = tuple(
            value for value in credential.values() if isinstance(value, str)
        )
        safe_result = _redact(raw_result, secret_values)
        response_hash = _digest(safe_result)
        source_urls_raw = (
            safe_result.get("source_urls", [])
            if isinstance(safe_result, dict) else []
        )
        source_urls = tuple(
            str(url) for url in source_urls_raw if isinstance(url, str)
        )
        receipt = KeyholeReceipt(
            receipt_id=f"khr_{secrets.token_hex(8)}",
            grant_id=grant.grant_id,
            subject_id=grant.subject_id,
            task_type=task_type,
            provider=locker.provider,
            credential_fingerprint=locker.secret_fingerprint,
            requested_capability=requested_capability,
            request_hash=request_hash,
            response_hash=response_hash,
            authorization_result="ALLOWED",
            redaction_passed=True,
            created_at=_iso(_utcnow()) or "",
            source_urls=source_urls,
        )
        self._receipts.append(receipt)
        if grant.requests_used >= grant.request_budget:
            grant.status = GrantStatus.EXHAUSTED
        return {"ok": True, "result": safe_result, "receipt": receipt.to_dict()}

    def receipts(self, *, subject_id: str | None = None) -> list[dict[str, Any]]:
        values = self._receipts
        if subject_id is not None:
            values = [r for r in values if r.subject_id == subject_id]
        return [r.to_dict() for r in values]

    def _denied(
        self,
        grant: KeyholeGrant,
        task_type: str,
        requested_capability: str,
        payload: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        locker = self._keybox._get_locker(grant.locker_id)
        receipt = KeyholeReceipt(
            receipt_id=f"khr_{secrets.token_hex(8)}",
            grant_id=grant.grant_id,
            subject_id=grant.subject_id,
            task_type=task_type,
            provider=locker.provider,
            credential_fingerprint=locker.secret_fingerprint,
            requested_capability=requested_capability,
            request_hash=_digest(_redact(payload)),
            response_hash=None,
            authorization_result=f"DENIED:{reason}",
            redaction_passed=True,
            created_at=_iso(_utcnow()) or "",
        )
        self._receipts.append(receipt)
        return {"ok": False, "error": reason, "receipt": receipt.to_dict()}

    def _get_grant(self, grant_id: str) -> KeyholeGrant:
        if grant_id not in self._grants:
            raise KeyError(f"Unknown grant: {grant_id}")
        return self._grants[grant_id]

    @staticmethod
    def _refresh_grant(grant: KeyholeGrant) -> None:
        if grant.status == GrantStatus.OPEN and grant.is_expired():
            grant.status = GrantStatus.EXPIRED
