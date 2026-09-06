# FARI Scenario Test Catalog

Seeded workspace catalog for the local FARI demo database.

This release edition keeps the canonical scenario coverage while presenting
each assessment as a compact executive record.

## Coverage summary

- `Does Not Meet`, `Meets`, `Inconclusive`, and `Not Assessed` are represented.
- `Demonstrated`, `Plausible`, `Not Demonstrated`, and `Not Evaluated` are represented.
- Traceability examples include mitigation and asset-source lifecycle revisions.

## Assessment portfolio

### ASM-2026-0001 Command Auth Fallback Review

- Current result: `does_not_meet`
- Scenario disposition: `demonstrated`
- Versions: v1: Initial confirmed bypass / v2: Residual maintenance bridge remains open
- Notes: Partial mitigation that still fails.

### ASM-2026-0002 Privileged Operator MFA Rollout

- Current result: `meets`
- Scenario disposition: `not_demonstrated`
- Versions: v1: Password-only access / v2: MFA enforced and retested
- Notes: Clean mitigation success.

### ASM-2026-0003 Replay Window Characterization

- Current result: `inconclusive`
- Scenario disposition: `plausible`
- Versions: v1: Short-window replay retest only
- Notes: Longer-window validation remains pending.

### ASM-2026-0004 Telemetry API RBAC Review

- Current result: `meets`
- Scenario disposition: `not_demonstrated`
- Versions: v1: RBAC and audit controls confirmed
- Notes: Cloud reference success case.

### ASM-2026-0005 Third-Party Firmware Intake

- Current result: `not_assessed`
- Scenario disposition: `not_evaluated`
- Versions: v1: Intake-only snapshot
- Notes: Non-gating draft intake.

### ASM-2026-0006 Asset Source Vulnerability Lifecycle

- Current result: `meets`
- Scenario disposition: `not_demonstrated`
- Versions: v1: Vulnerable baseline / v2: Fixed dependency confirmed
- Notes: Asset-source and inventory-event traceability example.

### ASM-2026-0007 Command-Link Confidentiality Rehearsal

- Current result: `meets`
- Scenario disposition: `plausible`
- Versions: v1: Scoped result based on compensating controls
- Notes: Meets result with an explicit boundary.

### ASM-2026-0008 Operational LEO Reset Command Replay

- Current result: `does_not_meet`
- Scenario disposition: `demonstrated`
- Versions: v1: Initial event and evidence intake / v2: Execution, telemetry impact, and unresolved attribution recorded
- Notes: Operational LEO example combining strong execution evidence with missing backup-station records and incomplete physical transmitter attribution.

## Filter expectations

- Portfolio filters should show closed assessments in `meets`, `does_not_meet`, and `inconclusive`.
- The draft intake case should keep a genuine `not_assessed` overall state.

## Suggested demo order

1. `ASM-2026-0001` for a partial mitigation that still fails.
2. `ASM-2026-0002` for a clean mitigation success.
3. `ASM-2026-0003` for a defensible inconclusive result.
4. `ASM-2026-0005` for a true draft intake.
5. `ASM-2026-0006` for asset-source-driven continuous assurance.
6. `ASM-2026-0008` for demonstrated operational effect with incomplete source attribution.
