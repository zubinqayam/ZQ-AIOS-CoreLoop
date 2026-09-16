# ZQ KeyBox + Keyhole Powerhouse v1

A deliberately small credential-routing and authorization layer for the ZQ Search Brain and AutoTechServ discovery workflows.

## Purpose

The Powerhouse gives applications one safe path for approved provider access:

```text
KeyBox metadata + protected secret reference
                |
                v
short-lived Keyhole grant
(subject + capability + TTL + request budget)
                |
                v
provider adapter executes server-side
                |
                v
redacted result + SHA-256 receipt
```

It does **not** copy browser sessions, collect provider passwords, bypass provider controls, or make every connected account a permanent master key.

## v1 surface

- `SimpleKeyBox.connect_api_key(...)`
- `SimpleKeyBox.connect_oauth(...)`
- masked locker listings and account display
- disable / revoke controls
- `KeyholePowerhouse.open(...)` for subject-scoped grants
- capability, TTL, and request-budget enforcement
- provider adapter routing
- recursive secret redaction
- request/response SHA-256 receipts
- source URL carry-through for downstream evidence envelopes

## Recommended AutoTechServ pilot policy

Allowed capabilities:

- `search.public`
- `drive.read`
- `sharepoint.read`
- `github.read`
- `llm.generate_draft`

Keep these separate and blocked until explicitly introduced with HITL approval:

- `email.send`
- `crm.write`
- `drive.write`
- `calendar.write`
- `profile.edit`
- `form.submit`
- browser-cookie or password import

## Secret-store rule

`InMemorySecretStore` exists only for development and unit tests.

Production wiring must provide a `SecretStore` backed by an OS keychain, KMS/HSM, or dedicated secret vault. Search memory, DDC capsules, receipts, logs, frontend state, and Git repositories must contain references/fingerprints only.

## OAuth rule

The v1 class accepts tokens only after a provider-specific OAuth flow has completed. It is **not** an OAuth authorization server or browser-login implementation. Provider OAuth adapters should own authorization URL generation, callback validation, refresh, revocation, and scope verification.

## Integration point

The existing `core/keyhole_gateway.py` remains the enterprise trust-plane contract. This v1 module is a small application-facing façade/pattern that can be wired into the Search Brain console without weakening the rule that provider access must route through a Keyhole boundary.
