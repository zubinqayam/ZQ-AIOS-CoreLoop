# ZQ Cognitive Overlay System™ v1 Runtime Architecture Contract

**Version:** 1.0.0  
**Status:** FROZEN  
**Effective Date:** May 21, 2026  
**Author:** Zubin Qayam, ZQ AI LOGIC™  
**License:** Apache 2.0

---

## Executive Summary

This document constitutes the **constitutional runtime layer** for the ZQ Cognitive Overlay System (ZQ-AIOS-CoreLoop), including all dependent subsystems:

- **AutoserGPT-T1** (Taskmaster orchestration)
- **ZQ_KEYBOX** (credential vault)
- **Keyhole Runtime Gateway** (enterprise trust plane)
- **Replayable Cognitive Memory** (event-sourced state)
- **ALGA Governance Infrastructure** (validation layer)
- **Sentinel** (observation layer)

The system transitions from **conceptual AI workspace** to **runtime-governed cognitive infrastructure** designed for enterprise deployment in:

- Healthcare operations
- Industrial operations
- Regulated environments
- Multi-agent automation
- AI governance and compliance

**Core Architecture Principle:**  
Event-Sourced, Deterministic, Replayable, Governable-by-Design

---

## 1. System Architecture Overview

### 1.1 Four-Layer Separation

The runtime enforces strict separation across four logical planes:

| Layer | Responsibility | Trust Boundary |
|-------|---------------|----------------|
| **Conversation Layer** | User interaction, workspace overlays | User-facing |
| **Orchestration Layer** | Taskmaster, agent coordination | Internal |
| **Monitoring Layer** | Sentinel, ALGA validation | Non-blocking async |
| **Provider Security** | Keybox, Keyhole gateway | Credential isolation |

### 1.2 Event-First Foundation

All state transitions MUST be:

- **Event-Sourced**: Every action produces an immutable event
- **Deterministic**: SHA256-hashed identifiers for stable naming
- **Replayable**: Full execution reconstruction from event log
- **Observable**: All actions attributable and traceable

### 1.3 Local-to-Enterprise Hybrid

```
LOCAL EDGE RUNTIME:
  Workspace Runtime → Taskmaster → Keyhole → SQLite WAL → Async Sidecar

ENTERPRISE CORE (Optional):
  NATS JetStream → Replay Engine → ALGA → Analytics
```

---

## 2. Event Standards

### 2.1 Core Event Schema

All events MUST include:
- `event_id`: SHA256(timestamp + source + type + nonce)
- `event_type`: TASK_CREATED | PROVIDER_INVOKED | etc.
- `timestamp`: ISO8601 UTC
- `correlation_id`: Request trace ID
- `source`: Component ID (taskmaster | keyhole | sentinel)
- `payload`: Type-specific data
- `signature`: HMAC-SHA256

### 2.2 Event Immutability

- Events are **append-only**
- Events CANNOT be deleted (only superseded)
- Event ordering MUST be preserved
- Cryptographic signatures required

---

## 3. SQLite WAL Contract

### 3.1 Local Persistence

SQLite is the **immutable local event ledger**.

**Allowed:** INSERT, SELECT, CREATE INDEX  
**Prohibited:** UPDATE events, DELETE FROM events

### 3.2 WAL Mode

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
```

### 3.3 Event Retention

- Local: 30 days rolling
- Enterprise: Indefinite
- Replay snapshots: 90 days compressed

---

## 4. Async Boundaries

### 4.1 Critical Path (< 150ms total)

| Operation | Target |
|-----------|--------|
| Keyhole routing | < 50ms |
| Taskmaster dispatch | < 80ms |
| Provider handoff | < 30ms |
| SQLite WAL append | < 10ms |

### 4.2 Non-Critical Path (Async)

- ALGA validation (< 5ms enqueue)
- Replay indexing (background)
- Sentinel observation (non-blocking)
- Telemetry (batch)

---

## 5. Provider Trust Model

### 5.1 Keyhole Gateway

The **Keyhole** is the exclusive interface between:
- Execution (Taskmaster)
- Providers (LLMs, APIs)
- Credentials (Keybox)

**Security:**
- Providers CANNOT access Keybox directly
- All credential access logged
- Requests scoped by workspace + user + policy

### 5.2 Provider Request Flow

```
1. Taskmaster → Keyhole.request_provider()
2. Keyhole → Policy validation
3. Keyhole → Keybox.fetch_credential()
4. Keyhole → Provider API execution
5. Keyhole → Event log: PROVIDER_EXECUTED
6. Return response
```

### 5.3 Failover

- Primary failure → fallback provider
- All fail → human escalation
- Circuit breaker: 3 failures = OFFLINE

---

## 6. Replay Guarantees

### 6.1 Deterministic Replay

Given events E1...En, replay MUST:
- Reconstruct identical state
- Produce identical outputs (modulo timestamps)
- Respect causal ordering

### 6.2 Replay Modes

- **Point-in-Time**: Reconstruct at timestamp T
- **Causal Chain**: Replay from correlation_id
- **Simulation**: Replay without side effects
- **Audit**: Replay with full validation

---

## 7. Enterprise Deployment

### 7.1 v1 Profile (ONLY)

**Enterprise Proxy Mode + Compliance Replay**

- All provider requests → Centralized Keyhole
- All events → Enterprise NATS
- All execution → Observable & replayable
- All credentials → Centralized Keybox

### 7.2 Security Requirements

**Observable Non-Autonomy:**
- Every execution attributed
- Every action replayable
- Every credential access logged
- Every policy violation triggers alert

**Prohibited in v1:**
- Autonomous execution without approval
- Offline provider execution
- Peer-to-peer orchestration
- Unmanaged overlays

---

## 8. Failure Recovery

### 8.1 Provider Timeout

- Retry: 3 attempts, exponential backoff
- Timeout: 30s/attempt
- Fallback: Alternative provider or escalate

### 8.2 SQLite Corruption

- Halt local runtime
- Sync from enterprise
- Rebuild local WAL

### 8.3 NATS Unavailable

- Continue local-only
- Buffer events (max 10K)
- Resume sync when restored

---

## 9. Compliance & Audit

### 9.1 Audit Trail

Every execution traceable through:
1. Correlation ID (end-to-end trace)
2. Causation ID (parent-child)
3. User attribution (WHO)
4. Workspace context (WHERE)
5. Provider log (WHAT)
6. Replay record (HOW)

### 9.2 Retention

| Data | Retention |
|------|----------|
| Events | 90d local, indefinite enterprise |
| Replays | 90d compressed |
| Credentials | Until revoked |
| Telemetry | 30d |

---

## 10. Prohibited Actions (v1)

❌ Autonomous execution without approval  
❌ Direct SQLite modifications  
❌ Credential access outside Keyhole  
❌ Blocking operations on critical path  
❌ Unbounded recursive orchestration  
❌ Cross-workspace event injection  
❌ Replay without audit trail  
❌ Offline providers in Enterprise Mode  

---

## 11. Contract Enforcement

### Runtime Validation

On startup, verify:
- Event schema compatibility
- SQLite WAL enabled
- Keyhole reachable
- ALGA responsive
- Replay engine functional

### Violation Response

1. Log critical incident
2. Halt affected component
3. Generate incident report
4. Notify operations
5. DO NOT auto-recover

---

## 12. Next Steps

1. Implement Local Runtime (SQLite + Taskmaster + Keyhole)
2. Build Enterprise Core (NATS + Replay + ALGA)
3. Deploy v1 Pilot (Healthcare customer)
4. Load Testing & Optimization
5. Expand to v2 Modes (Air-gapped, Local-Only)

---

## Conclusion

This contract establishes the **immutable foundation** for ZQ Cognitive Overlay System v1.

Further architectural ideation provides **diminishing returns** until validated through production deployment.

**Status:** FROZEN  
**Authority:** Zubin Qayam, ZQ AI LOGIC™  
**Enforcement Date:** May 21, 2026

---

© 2026 Zubin Qayam. All rights reserved. ZQ AI LOGIC™
