# ZQ Cognitive Overlay System™
## DETERMINISM_TEST_MATRIX

**Version:** 1.0.0  
**Status:** ACTIVE  
**Effective Date:** May 21, 2026  
**Authority:** CONTRACT_COMPLIANCE.md Amendment 1 (0a7c84a)  
**Author:** Zubin Qayam, ZQ AI LOGIC™

---

## Purpose

This matrix is the **runtime survivability validation** document for ZQ-AIOS-CoreLoop.

It tracks every determinism guarantee the system makes and defines how each is verified.
A system that cannot pass this matrix is **not enterprise infrastructure** — it is a prototype.

This document becomes CI-blocking infrastructure. Every row with `CI Gate: Yes` must pass
before Phase 3 (Enterprise Core) work begins.

---

## Matrix Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Test exists and passing |
| ⚠️ | Test exists, not yet passing |
| 🔴 | Test does NOT exist yet |
| 🚫 | Explicitly prohibited (do not implement) |

---

## Section 1 — Replay Correctness

| # | Guarantee | Test Description | CI Gate | Status |
|---|-----------|-----------------|---------|--------|
| 1.1 | Deterministic replay: same input → same output | Replay identical event sequence twice; compare output hash | Yes | 🔴 |
| 1.2 | Sequence-ID ordering is the ONLY replay ordering mechanism | Inject events out of timestamp order; verify replay uses sequence_id | Yes | 🔴 |
| 1.3 | Hash-chain continuity across full WAL | Verify every event’s previous_event_hash matches prior event’s SHA-256 | Yes | 🔴 |
| 1.4 | Sequence-gap detection | Inject gap in sequence_id; verify ReplayEngine raises SequenceGapError | Yes | 🔴 |
| 1.5 | Ordering invariance under concurrent appends | 50 concurrent producers append; verify replay sequence is strictly monotonic | Yes | 🔴 |
| 1.6 | Time-window replay returns deterministic bounded set | Replay events within [T1, T2]; verify same events returned across runs | Yes | 🔴 |
| 1.7 | Failure reconstruction from partial WAL | Truncate WAL mid-session; replay to last VERIFIED event; verify reconstruction | Yes | 🔴 |

---

## Section 2 — Timing Guarantees

| # | Guarantee | Measurement Method | Target | CI Gate | Status |
|---|-----------|-------------------|--------|---------|--------|
| 2.1 | Queue enqueue latency | Measure time from `append()` call to queue ACK | < 1ms | No | 🔴 |
| 2.2 | Micro-batch window duration | Measure actual batch collection window | ≤ 2ms | Yes | 🔴 |
| 2.3 | Total append confirmation latency | Measure time from `append()` to `APPENDED` state | 10–25ms | Yes | 🔴 |
| 2.4 | Critical path orchestration budget | Measure agent dispatch to queue ACK | < 5ms | Yes | 🔴 |
| 2.5 | Keyhole hot-path policy cache latency | Measure Tier 1 policy lookup | < 2ms | Yes | 🔴 |
| 2.6 | Latency under 100 concurrent producers | Run flood test; measure p95 append latency | < 50ms | Yes | 🔴 |
| 2.7 | Latency alert threshold | Verify alert fires when append > 50ms | Alert fires | No | 🔴 |

---

## Section 3 — Ordering Guarantees

| # | Guarantee | Test Description | CI Gate | Status |
|---|-----------|-----------------|---------|--------|
| 3.1 | sequence_id is strictly monotonic (never reused) | Append 10,000 events; verify no duplicate sequence_id | Yes | 🔴 |
| 3.2 | sequence_id is atomic (concurrent-safe) | 100 concurrent producers; verify no two events share sequence_id | Yes | 🔴 |
| 3.3 | WAL offset is stable (no rewrite) | Append events; verify wal_offset never changes for committed events | Yes | 🔴 |
| 3.4 | No UPDATE or DELETE ever executes against WAL | Inspect SQLite WAL file; verify only INSERT statements present | Yes | 🔴 |
| 3.5 | Event envelope fields are immutable after APPENDED | Attempt field mutation after commit; verify ImmutableEventError raised | Yes | 🔴 |

---

## Section 4 — Crash Recovery

| # | Scenario | Expected Behavior | CI Gate | Status |
|---|----------|------------------|---------|--------|
| 4.1 | Power loss mid-fsync | Restart; ReplayEngine replays only VERIFIED events; DISPATCHED events not present | Yes | 🔴 |
| 4.2 | Writer crash mid-queue | Restart; queue drained from last APPENDED event; no phantom events | Yes | 🔴 |
| 4.3 | WAL file truncation | Open truncated WAL; verify graceful truncation detection and error report | Yes | 🔴 |
| 4.4 | Partial transaction commit | Simulate partial write; verify rollback; last complete transaction is canonical | Yes | 🔴 |
| 4.5 | Kill-Writer test | Crash writer mid-queue; restart; verify hash-chain self-heals or flags exact truncation | Yes | 🔴 |
| 4.6 | Recovery mode activation | Trigger RECOVERY state; verify orchestration halts; replay proceeds | Yes | 🔴 |
| 4.7 | Hash-chain self-heal detection | Inject corruption; verify CorruptionDetectedError with exact offset | Yes | 🔴 |

---

## Section 5 — WAL Corruption Handling

| # | Scenario | Expected Behavior | CI Gate | Status |
|---|----------|------------------|---------|--------|
| 5.1 | Single event hash corrupted | Detect mismatch; raise TamperDetectedError; halt replay at corruption point | Yes | 🔴 |
| 5.2 | HMAC signature invalid | Reject event; log forensic audit entry; raise HMACVerificationError | Yes | 🔴 |
| 5.3 | sequence_id jump (gap injection) | Raise SequenceGapError with gap start and end | Yes | 🔴 |
| 5.4 | previous_event_hash mismatch | Raise ChainBreakError; mark all subsequent events as unverified | Yes | 🔴 |
| 5.5 | WAL file locked by external process | Return WALLockError; do not silently fail | Yes | 🔴 |

---

## Section 6 — Provider Replay Equivalence

| # | Guarantee | Test Description | CI Gate | Status |
|---|-----------|-----------------|---------|--------|
| 6.1 | Provider call envelope is deterministic | Same request params → same serialized envelope hash | Yes | 🔴 |
| 6.2 | KeyholeGateway is the only provider ingress | Static analysis confirms no direct provider imports outside Keyhole | Yes | 🔴 |
| 6.3 | Credential fetch does NOT occur inline | Verify no vault call inside `route_request()` critical path | Yes | 🔴 |
| 6.4 | Revoked credential replay blocked | Attempt replay with revoked token; verify PermissionDeniedError raised | Yes | 🔴 |
| 6.5 | Provider timeout triggers circuit breaker | Simulate provider timeout; verify circuit breaker activates; no retry storm | Yes | 🔴 |

---

## Section 7 — Backpressure and Queue Health

| # | Guarantee | Test Description | CI Gate | Status |
|---|-----------|-----------------|---------|--------|
| 7.1 | DEGRADED state triggers at 50% queue depth | Fill queue to 50%; verify DEGRADED state emitted | Yes | 🔴 |
| 7.2 | THROTTLED state triggers at 75% queue depth | Fill queue to 75%; verify THROTTLED state + agent fanout reduced | Yes | 🔴 |
| 7.3 | CRITICAL state triggers at 90% queue depth | Fill queue to 90%; verify new orchestration rejected | Yes | 🔴 |
| 7.4 | RECOVERY mode halts orchestration | Simulate crash; verify RECOVERY state blocks new dispatches | Yes | 🔴 |
| 7.5 | Backpressure signal propagates to Taskmaster | CRITICAL state → verify Taskmaster receives throttle signal | Yes | 🔴 |
| 7.6 | Queue never silently overflows | Overflow attempt → QueueFullError raised; not silent discard | Yes | 🔴 |

---

## Section 8 — Explicitly Prohibited (Do Not Test — Do Not Implement)

These capabilities are **prohibited in Phase 2**. Do not write tests for them.
Do not implement stubs. Do not add TODOs for them in Phase 2 code.

| Prohibited Feature | Reason |
|--------------------|---------|
| Branching replay | Collapses determinism baseline |
| Speculative replay | Introduces non-canonical truth |
| Distributed replay merge | Phase 3+ only |
| Causal graph replay | Premature complexity |
| Probabilistic reconstruction | Incompatible with audit credibility |
| Floating overlays before WAL proven | Governance collapse risk |
| Autonomous agents before trust enforcement proven | Attribution collapse |

---

## Current Overall Status

| Section | Total Tests | Passing (✅) | Pending (🔴) | Blocked (⚠️) |
|---------|-------------|------------|------------|------------|
| 1 — Replay Correctness | 7 | 0 | 7 | 0 |
| 2 — Timing Guarantees | 7 | 0 | 7 | 0 |
| 3 — Ordering Guarantees | 5 | 0 | 5 | 0 |
| 4 — Crash Recovery | 7 | 0 | 7 | 0 |
| 5 — WAL Corruption | 5 | 0 | 5 | 0 |
| 6 — Provider Replay Equiv. | 5 | 0 | 5 | 0 |
| 7 — Backpressure | 6 | 0 | 6 | 0 |
| **TOTAL** | **42** | **0** | **42** | **0** |

**Phase 3 Gate:** All 42 CI-blocking tests must be ✅ before Enterprise Core work begins.

---

## Update Instructions

When a test is implemented and passing:
1. Change status from 🔴 to ✅
2. Update the section totals table
3. Commit with message: `test(determinism): [section].[number] — [test name]`

When a test is implemented but failing:
1. Change status from 🔴 to ⚠️
2. Open a blocking issue referencing this matrix row
3. Do NOT proceed to Phase 3 until resolved

---

**Document Authority:** Zubin Qayam, ZQ AI LOGIC™  
**Next Review:** When first 10 tests reach ✅ status  
**Ref:** CONTRACT_COMPLIANCE.md Amendment 1, RUNTIME_CONTRACT_v1.md
