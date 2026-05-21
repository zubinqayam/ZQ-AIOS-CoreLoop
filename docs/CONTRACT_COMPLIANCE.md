# ZQ Cognitive Overlay System™
# Contract Compliance & Enforcement Doctrine

**Version:** 1.0.0  
**Status:** ACTIVE  
**Effective Date:** May 21, 2026  
**Authority:** RUNTIME_CONTRACT_v1.md (bdad753)  
**Author:** Zubin Qayam, ZQ AI LOGIC™

---

## Purpose

This document is the **operational enforcement doctrine** for the ZQ Cognitive Overlay System runtime contract.

While `RUNTIME_CONTRACT_v1.md` defines WHAT is required,
this document defines HOW compliance is verified, enforced, and protected.

Every engineer, contributor, and automated system working on:
- ZQ-AIOS-CoreLoop
- AutoserGPT-T1 (Taskmaster)
- ZQ_KEYBOX
- Keyhole Runtime Gateway
- Replayable Cognitive Memory
- ALGA Governance Infrastructure
- Sentinel

MUST treat this document as **non-negotiable operational law**.

---

## Part 1 — Prohibited Implementation Shortcuts

The following are **absolutely prohibited** in all implementations.
No exception. No workaround. No "temporary" bypass.

### 1.1 Event System Violations

| Prohibition | Reason |
|-------------|--------|
| Modifying an existing event record | Destroys replay determinism |
| Deleting events for cleanup | Destroys audit trail |
| Writing events without SHA256 ID | Breaks duplicate detection |
| Writing events without HMAC signature | Breaks integrity verification |
| Inserting events out of causal order | Corrupts replay reconstruction |
| Using mutable IDs (timestamps, UUIDs alone) | Breaks stable variable naming |
| Batching events without ordering guarantee | Introduces non-determinism |

### 1.2 Keyhole Bypass Violations

| Prohibition | Reason |
|-------------|--------|
| Accessing provider APIs directly (not through Keyhole) | Breaks trust boundary |
| Reading credentials from Keybox without Keyhole | Breaks credential scoping |
| Spawning provider sub-processes outside Keyhole | Creates unobservable execution |
| Caching provider tokens outside Keybox | Creates credential leakage |
| Routing LLM calls through undeclared paths | Breaks attribution |

### 1.3 Async Boundary Violations

| Prohibition | Reason |
|-------------|--------|
| Calling ALGA.validate() synchronously on critical path | Destroys latency guarantee |
| Awaiting Sentinel.observe() before execution | Blocks orchestration |
| Waiting for replay log confirmation before response | Violates < 150ms target |
| Blocking provider handoff on telemetry flush | Destroys user experience |
| Making analytics processing synchronous | Critical path contamination |

### 1.4 Replay Non-Determinism Violations

| Prohibition | Reason |
|-------------|--------|
| Using wall clock time as event ordering source | Clock skew destroys ordering |
| Generating random values during replay | Breaks deterministic reconstruction |
| Making external API calls during simulation replay | Produces inconsistent state |
| Replaying without verifying HMAC signatures | Accepts corrupted events |
| Skipping causation_id chains during causal replay | Produces incomplete state |

### 1.5 SQLite Violations

| Prohibition | Reason |
|-------------|--------|
| Running SQLite without WAL mode | Loses concurrent read safety |
| Updating event rows post-insert | Mutates immutable ledger |
| Deleting events for storage reclaim | Destroys local audit trail |
| Using SQLite for enterprise-scale fanout | Hits write-lock ceiling |
| Running schema migrations on event tables without version bump | Breaks schema compatibility |

---

## Part 2 — Mandatory Replay Tests

Every release MUST pass the following replay validation suite before merge to `main`.

### 2.1 Core Replay Tests

```
TEST: replay_determinism
  Given: event sequence E1...En
  When: replayed twice from same starting state
  Then: output state S1 == S2
  Tolerance: none
```

```
TEST: replay_causal_ordering
  Given: events with causation_id chains
  When: replayed in causal order
  Then: child events always processed after parent events
  Tolerance: none
```

```
TEST: replay_integrity
  Given: event log with HMAC signatures
  When: replay engine processes events
  Then: all HMAC signatures verified before processing
  On failure: replay aborts, incident logged
```

```
TEST: replay_simulation_isolation
  Given: simulation mode replay
  When: replaying provider execution events
  Then: NO external API calls made
  Then: NO database writes executed
  Then: NO credentials accessed
```

```
TEST: replay_point_in_time
  Given: event log spanning T1...T100
  When: replay_to(T50) called
  Then: state identical to original state at T50
  Tolerance: none
```

### 2.2 Failure Recovery Tests

```
TEST: wal_corruption_recovery
  Given: SQLite WAL file corrupted
  When: runtime detects corruption on startup
  Then: runtime halts cleanly
  Then: incident log created
  Then: sync from enterprise initiated
  Then: NO silent data loss
```

```
TEST: nats_disconnect_recovery
  Given: NATS enterprise cluster becomes unreachable
  When: async sidecar sync fails
  Then: local runtime continues operating
  Then: events buffered (max 10,000)
  Then: sync resumes when connection restored
  Then: NO events lost
```

---

## Part 3 — Event Validation Requirements

All events entering the system MUST be validated against these rules before acceptance.

### 3.1 Schema Validation

- [ ] `event_id` present and matches SHA256(timestamp + source + type + nonce)
- [ ] `event_type` is a recognized enum value
- [ ] `timestamp` is valid ISO8601 UTC
- [ ] `source` is a declared component ID
- [ ] `correlation_id` present (required)
- [ ] `payload` conforms to type-specific schema
- [ ] `signature` present and valid HMAC-SHA256
- [ ] `metadata.version` present and recognized

### 3.2 Ordering Validation

- [ ] `causation_id` references an existing parent event (if present)
- [ ] Event timestamp not earlier than system epoch
- [ ] Event ID not already present in WAL (duplicate detection)

### 3.3 Rejection Behavior

An event failing validation MUST:
1. Be **rejected** (not silently dropped)
2. Generate a `VALIDATION_FAILED` governance event
3. Log the rejection with full details
4. NOT corrupt the existing event sequence

---

## Part 4 — Timing Enforcement Checks

The following timing SLAs MUST be monitored on every production deployment.

### 4.1 Critical Path Budget

| Operation | Hard Limit | Alert Threshold | Action if Exceeded |
|-----------|-----------|-----------------|--------------------|
| Keyhole routing | 50ms | 40ms | Alert ops |
| Taskmaster dispatch | 80ms | 60ms | Alert ops |
| Provider handoff | 30ms | 25ms | Alert ops |
| SQLite WAL append | 10ms | 8ms | Alert ops |
| **Total orchestration** | **150ms** | **120ms** | **Page on-call** |

### 4.2 Async Side Channel Limits

| Operation | Enqueue Limit | Alert if blocked |
|-----------|--------------|------------------|
| ALGA validation enqueue | 5ms | Yes |
| Sentinel observation fire | 2ms | Yes |
| Replay log enqueue | 10ms | Yes |
| Telemetry emit | 1ms | Yes |

### 4.3 Timing Enforcement Rule

If any async side channel blocks the critical path for > 5ms:
1. Log `ASYNC_BOUNDARY_VIOLATION` event
2. Alert operations
3. Treat as **P1 incident** requiring immediate remediation

---

## Part 5 — Schema Migration Rules

Event schemas are **constitutional** — changes require formal process.

### 5.1 Allowed Without Version Bump (PATCH)
- Adding optional fields with null default
- Adding new event types
- Extending enum values
- Documentation updates

### 5.2 Requires MINOR Version Bump
- Adding required fields with backward-compatible defaults
- Deprecating fields (must remain in schema)
- Changing field descriptions

### 5.3 Requires MAJOR Version Bump
- Removing any field
- Changing field types
- Reordering mandatory fields
- Breaking HMAC signature scheme
- Changing event ID generation algorithm

### 5.4 Migration Process

1. Draft schema change proposal
2. Impact assessment on existing replay corpus
3. Backward compatibility test suite pass
4. Update RUNTIME_CONTRACT_v1.md (or next version)
5. Deploy with dual-read support for 1 full release cycle
6. Remove deprecated fields only on next MAJOR version

---

## Part 6 — Failure Modes to Guard Against

These are the three most dangerous failure modes identified in strategic assessment.
Each has specific countermeasures.

### 6.1 Silent Contract Drift

**Risk:** Developers bypassing event standards, replay semantics, or Keyhole routing under time pressure.

**Countermeasures:**
- Code review MUST reject any direct provider API call outside Keyhole
- CI MUST run event schema validation on every PR
- MUST run replay determinism test on every PR touching event code
- Weekly contract compliance review meeting

### 6.2 Side-Channel Leakage into Critical Path

**Risk:** ALGA/Sentinel/analytics slowly re-entering synchronous execution flow.

**Countermeasures:**
- All governance calls MUST be async-only (enforced by interface type)
- Critical path code MUST NOT import Sentinel or ALGA modules directly
- Timing tests run on every release (see Part 4)
- Architectural review required for any change to orchestration dispatch

### 6.3 Replay Non-Determinism

**Risk:** Clock inconsistency, mutable events, or provider nondeterminism destroying audit credibility.

**Countermeasures:**
- Logical clocks (Lamport or vector) MUST be used for event ordering
- Wall clock used ONLY for human-readable timestamps, not ordering
- All external calls during replay MUST be mocked or rejected
- HMAC verification MUST precede every event processing step
- Replay non-determinism detected = P0 incident

---

## Part 7 — Implementation Checklist for Priority Components

### Priority 1: EventAppender

- [ ] Generates SHA256 event_id from (timestamp + source + type + nonce)
- [ ] Computes HMAC-SHA256 signature before write
- [ ] Appends to SQLite WAL in append-only mode
- [ ] Validates no duplicate event_id before insert
- [ ] Rejects any call to UPDATE or DELETE event rows
- [ ] Returns event_id on success
- [ ] Emits `VALIDATION_FAILED` on schema violation
- [ ] < 10ms write latency under normal load

### Priority 2: ReplayEngine

- [ ] Reads events from WAL in causal order
- [ ] Verifies HMAC signature on every event before processing
- [ ] Supports Point-in-Time replay to timestamp T
- [ ] Supports Causal Chain replay from correlation_id
- [ ] Supports Simulation Mode (no side effects)
- [ ] Supports Audit Mode (full validation logging)
- [ ] Produces identical output for identical input (determinism test)
- [ ] NO external API calls in Simulation Mode
- [ ] Generates audit report on completion
- [ ] Built BEFORE overlays, agents, or federation

### Priority 3: KeyholeGateway

- [ ] Single entry point for ALL provider requests
- [ ] Validates permission policy before credential fetch
- [ ] Fetches credentials from Keybox only (never cached externally)
- [ ] Logs `PROVIDER_REQUESTED` and `PROVIDER_EXECUTED` events
- [ ] Logs `CREDENTIAL_ACCESSED` for every credential fetch
- [ ] Enforces circuit breaker (3 failures = OFFLINE)
- [ ] Supports provider failover to secondary
- [ ] Routes to human escalation when all providers fail
- [ ] < 50ms routing overhead
- [ ] Rejects all direct provider bypass attempts with logged incident

---

## Part 8 — Incident Classification

| Incident Type | Severity | Response |
|---------------|----------|----------|
| Replay non-determinism detected | P0 | Halt + immediate remediation |
| Keyhole bypass detected | P0 | Halt + security review |
| Event mutation detected | P0 | Halt + forensic audit |
| Critical path > 150ms sustained | P1 | Alert + performance review |
| Async boundary violation | P1 | Alert + architecture review |
| Schema migration without version bump | P1 | Rollback + compliance review |
| NATS disconnect > 1 hour | P2 | Investigate + buffer check |
| ALGA validation failure rate > 5% | P2 | Review governance rules |

---

## Summary: The Non-Negotiables

These five principles are **absolute**. No exception at any phase:

1. **Events are immutable.** Append only. Forever.
2. **All providers route through Keyhole.** No bypass. Ever.
3. **Governance is async.** ALGA and Sentinel never block execution.
4. **Replay must be deterministic.** Same input, same output. Always.
5. **The contract is law.** Deviations require contract amendment, not workarounds.

---

**Status:** ACTIVE  
**Authority:** Zubin Qayam, ZQ AI LOGIC™  
**Enforcement Date:** May 21, 2026

---

© 2026 Zubin Qayam. All rights reserved. ZQ AI LOGIC™
