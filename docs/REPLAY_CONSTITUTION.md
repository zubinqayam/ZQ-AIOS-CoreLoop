# ZQ Cognitive Overlay System™
## REPLAY CONSTITUTION
### The Source of Truth Legitimacy Framework

**Version:** 1.0.0  
**Status:** ACTIVE — Constitutional Law  
**Effective Date:** May 22, 2026  
**Authority:** RUNTIME_CONTRACT_v1.md (bdad753), CONTRACT_COMPLIANCE.md Amendment 1 (0a7c84a)  
**Author:** Zubin Qayam, ZQ AI LOGIC™

---

## Preamble

This document establishes the **constitutional law of replay legitimacy** for ZQ-AIOS-CoreLoop.

The platform's enterprise credibility no longer depends on:
- Intelligence quality
- Model capability
- Provider performance
- Orchestration sophistication

It depends on:

> **Replayable Truth Preservation**

A system that cannot prove its history **cannot be sovereign infrastructure**.

This constitution defines **what replay means**, **what it guarantees**, and **how it is enforced**.

---

## Article I — Fundamental Principle

### Section 1.1 — Replay Equivalence Definition

**Replay equivalence** is the mathematical guarantee that:

```
Same Input WAL → Same Reconstructed State
```

Formally:

```
∀ (WAL₁, WAL₂) : WAL₁ ≡ WAL₂ ⟹ Replay(WAL₁) ≡ Replay(WAL₂)
```

Where `≡` denotes cryptographic hash equality.

**This is the foundational invariant of the platform.**

Any violation of replay equivalence is a **P0 constitutional breach**.

---

### Section 1.2 — State as Projection

**Agent State is NOT a record. It is an ephemeral projection computed dynamically from the ledger.**

This transition changes:
- Recovery
- Governance
- Replay
- Clustering
- CI
- Failover
- Observability
- Distributed scaling

**State does not exist independently of history.**  
**State IS the deterministic function of history.**

```python
state = f(WAL)
```

Not:

```python
state = db.get("current_state")
```

This is the **deepest architectural commitment** of the platform.

---

## Article II — Environment Determinism

### Section 2.1 — Environment Locking Requirement

Determinism is not merely **code determinism**.  
It is **environment determinism**.

Every replay MUST occur in a **historically sealed execution capsule** that locks:

| Dependency | Locking Mechanism | Mandatory |
|------------|-------------------|------------|
| Python version | `python_version.lock` | Yes |
| SQLite version | `sqlite_version.lock` | Yes |
| Timezone database | `tzdata.lock` | Yes |
| Dependency hashes | `dependency_hashes.lock` | Yes |
| RNG seed | `rng_seed.lock` | Yes |
| Floating-point ABI | `fp_abi.lock` | Yes |
| Schema version | `schema_version.lock` | Yes |

Without environment locking:
- Timezone updates cause replay drift
- SQLite version variance causes ordering drift
- Floating-point library updates cause computation drift
- Dependency updates cause logic drift

**Same code + different environment = different replay**

This is **mathematically inevitable**.

---

### Section 2.2 — Time Semantics

**Timestamps are NOT deterministic ordering primitives.**

The platform MUST use:

| Primitive | Purpose | Deterministic? |
|-----------|---------|----------------|
| `sequence_id` | Canonical ordering | Yes |
| Lamport clock | Logical causality | Yes |
| Epoch milliseconds | Human audit | No (but acceptable) |
| `datetime.now()` | **PROHIBITED** | No |
| ISO timestamp strings | **PROHIBITED** | No |
| Timezone-aware time | **PROHIBITED** | No |

**Rule:** Event ordering MUST be determined ONLY by `sequence_id`.  
Never by:
- Wall-clock time
- Arrival time
- Thread scheduling
- Asyncio completion order

---

### Section 2.3 — Randomness Semantics

All sources of non-determinism MUST be eliminated or controlled:

| Source | Status | Rule |
|--------|--------|------|
| `uuid.uuid4()` | **PROHIBITED** | Generate UUIDs externally and inject |
| `random.random()` | **PROHIBITED** | Use seeded PRNG with locked seed |
| `os.urandom()` | **PROHIBITED** | Use deterministic nonce from sequence |
| Lamport counter | **REQUIRED** | Single atomic allocator |
| Hash-chain nonce | **REQUIRED** | Derived from `prev_event_hash` |

**During replay:**
- RNG must be seeded identically
- All nonces must reconstruct identically
- All UUIDs must reconstruct from deterministic inputs

---

### Section 2.4 — External API Freezing

External API calls introduce **irreproducible non-determinism**.

**During replay:**
- Provider responses MUST be replayed from cache
- External HTTP calls MUST NOT execute
- Database queries MUST return historical snapshots
- File system reads MUST return frozen state

**Rule:** Replay MUST be **hermetically sealed** from external world state.

The only input to replay is:
```
WAL + Environment Capsule
```

---

## Article III — Hash-Chain Constitutional Law

### Section 3.1 — Cryptographic Continuity

Every event MUST be cryptographically linked to its predecessor.

**Required fields:**

```python
event_id = SHA256(
    prev_event_hash +
    sequence_id +
    payload_hash +
    timestamp +
    source +
    event_type
)
```

**Not:**

```python
event_id = SHA256(timestamp + uuid4())  # ❌ PROHIBITED
```

---

### Section 3.2 — Tamper Evidence

The hash-chain provides:

| Property | Guarantee |
|----------|------------|
| Tamper detection | Any payload mutation breaks the chain |
| Ordering proof | Events cannot be reordered without detection |
| Truncation detection | Missing events create hash mismatch |
| Insertion detection | Injected events break continuity |
| Replay equivalence | Same WAL → same hash sequence |

**Enforcement:** ReplayEngine MUST validate hash-chain continuity before accepting any event as canonical.

---

### Section 3.3 — Genesis Block

The WAL MUST begin with a **genesis event** that establishes the chain anchor.

```python
genesis_event = {
    "sequence_id": 0,
    "prev_event_hash": "0" * 64,  # SHA-256 zero hash
    "event_type": "GENESIS",
    "payload_hash": SHA256(runtime_contract_hash),
    "timestamp": epoch_ms(RUNTIME_CONTRACT_FREEZE_DATE),
}
```

All subsequent events MUST chain from genesis.

---

## Article IV — Schema Version Law

### Section 4.1 — Schema Immutability

**WAL schema changes are constitutional amendments.**

Every schema version MUST:
- Be explicitly declared in `schema_version` field
- Maintain backward compatibility
- Provide deterministic migration path
- Preserve hash-chain continuity across migrations

**PROHIBITED:**
- Silent schema mutations
- Implicit version bumps
- Non-deterministic migrations
- Lossy transformations

---

### Section 4.2 — Historical Compatibility Guarantees

**The platform MUST replay WALs from ANY historical schema version.**

This requires:
- Archived schema definitions for all versions
- Deterministic transformation functions
- Schema version validation in ReplayEngine
- Migration replay tests in CI

**Rule:** A 2030 system MUST replay a 2026 WAL identically.

---

## Article V — Floating-Point Rules

### Section 5.1 — Floating-Point Determinism

Floating-point arithmetic is **architecturally non-deterministic** across:
- CPU architectures (x86 vs ARM)
- Compiler optimization levels
- Math library versions
- Operating systems

**Required mitigations:**

| Mitigation | Enforcement |
|------------|-------------|
| Fixed-point arithmetic for money/metrics | Mandatory |
| Integer milliseconds for time | Mandatory |
| Decimal128 for precision-critical values | Recommended |
| FP operations logged with exact binary repr | Required for audit |

**PROHIBITED:**
- `float` arithmetic in state-critical logic
- Rounding without explicit mode declaration
- Comparison via `==` on floats

---

## Article VI — WAL Immutability Doctrine

### Section 6.1 — Append-Only Absolutism

**The WAL is append-only. Forever.**

| Operation | Status |
|-----------|--------|
| `INSERT` | Only legal operation |
| `UPDATE` | **PROHIBITED — P0 violation** |
| `DELETE` | **PROHIBITED — P0 violation** |
| `ALTER TABLE` | Constitutional amendment required |

**Enforcement:**
- AST-level static analysis in CI
- SQLite trigger guards
- File-level immutability flags

---

### Section 6.2 — Snapshot Verification Rules

Snapshots are **derivative artifacts**, not canonical truth.

**Every snapshot MUST include:**
```python
snapshot = {
    "state": computed_state,
    "wal_sequence_id": last_applied_event_id,
    "wal_hash": hash_of_last_event,
    "snapshot_hash": SHA256(state + wal_sequence_id),
    "created_at": epoch_ms,
}
```

**Snapshot validation:**
```python
assert Replay(WAL[:snapshot.wal_sequence_id]) == snapshot.state
```

---

## Article VII — Replay Execution Phases

### Section 7.1 — Phase Separation

Replay execution MUST occur in distinct phases:

| Phase | Behavior |
|-------|----------|
| **VALIDATION** | Hash-chain verification, schema validation |
| **SEQUENCING** | Ordering confirmation, gap detection |
| **PROJECTION** | State reconstruction from events |
| **VERIFICATION** | Final state hash comparison |

**Each phase is a CI gate.**

---

### Section 7.2 — Failure Modes

Replay can fail for exactly three reasons:

| Failure Type | Meaning | Action |
|--------------|---------|--------|
| `HashChainBroken` | Tamper detected | Halt at corruption point |
| `SequenceGap` | Missing events | Report gap bounds |
| `StateDivergence` | Replay ≠ expected state | Flag drift source |

**All other failures are bugs, not legitimate replay failures.**

---

## Article VIII — Enforcement

### Section 8.1 — CI Constitutional Enforcement

The CI pipeline MUST enforce replay legitimacy via:

```bash
pytest tests/test_replay_constitution.py --strict
```

Blocking tests:
- Deterministic replay (same WAL → same state)
- Hash-chain continuity
- Environment capsule validation
- Schema version compatibility
- Timestamp determinism
- RNG seed determinism

**Phase 3 gate: All constitutional tests MUST pass.**

---

### Section 8.2 — Bare-Metal Validation

**Virtualized CI runners LIE about fsync reliability.**

Critical tests MUST run on:
- Bare-metal hardware
- Real block devices
- Fault injection frameworks (dm-dust, dm-delay)
- Power-failure simulation

**Without bare-metal validation, determinism proof is incomplete.**

---

## Article IX — Amendment Process

This constitution can only be amended via:

1. Explicit proposal in governance review
2. Architectural impact assessment
3. Backward compatibility proof
4. Migration path definition
5. Unanimous sponsor approval
6. Version bump with audit trail

**Amendments are forever part of the ledger.**

---

## Article X — Supremacy Clause

In any conflict between:
- Code convenience
- Performance optimization
- Developer ergonomics
- Third-party library constraints

and:

- Replay equivalence  
- Constitutional determinism  
- Truth preservation

**The constitution prevails. Always.**

---

## Summary: The Nine Commandments of Replay

1. **State is a projection**, not a record.
2. **Ordering is sequence_id**, never timestamp.
3. **Environment is locked**, not assumed.
4. **Hashes form chains**, not isolated IDs.
5. **Schema is versioned**, not mutated.
6. **WAL is append-only**, forever.
7. **External APIs are frozen**, during replay.
8. **Floats are banned**, in state logic.
9. **Replay is the source of truth**, not the live system.

---

**Constitutional Authority:** Zubin Qayam, ZQ AI LOGIC™  
**Ratification Date:** May 22, 2026  
**Next Review:** When first constitutional test suite passes  
**Ref:** RUNTIME_CONTRACT_v1.md, CONTRACT_COMPLIANCE.md, DETERMINISM_TEST_MATRIX.md
