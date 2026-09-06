# FARI Scenario Test Catalog

Seeded workspace catalog for the local FARI demo database.

This release edition keeps the same portfolio coverage as the canonical source,
but restructures the assessment list for easier executive reading in PDF form.

## Coverage summary

- `Does Not Meet`: present in current state and in initial mitigation snapshots.
- `Meets`: present in clean success, mitigation-success, and compensating-control cases.
- `Inconclusive`: present as a closed replay-characterization case.
- `Not Assessed`: present as a draft non-gating intake case.
- Operational command replay: present as a demonstrated Does Not Meet case with explicit attribution gaps.
- `Demonstrated`, `Plausible`, `Not Demonstrated`, and `Not Evaluated` are all represented.

## Assessment portfolio

### `ASM-2026-0001` Command Auth Fallback Review

- Current result: ``does_not_meet``
- Scenario disposition: ``demonstrated``
- Versions: v1: Seeded state supported by EVD-0001-001.
- Notes: Partial mitigation case that remains Does Not Meet.

### `ASM-2026-0002` Privileged Operator MFA Rollout

- Current result: ``meets``
- Scenario disposition: ``not_demonstrated``
- Versions: v1: Seeded state supported by EVD-0002-001.
- Notes: Clean mitigation success with a clear audit trail.

### `ASM-2026-0003` Replay Window Characterization

- Current result: ``inconclusive``
- Scenario disposition: ``plausible``
- Versions: v1: Seeded state supported by EVD-0003-001.
- Notes: Inconclusive case pending longer-window validation.

### `ASM-2026-0004` Telemetry API RBAC Review

- Current result: ``meets``
- Scenario disposition: ``not_demonstrated``
- Versions: v1: Seeded state supported by EVD-0004-001.
- Notes: Cloud reference for a clean success case.

### `ASM-2026-0005` Third-Party Firmware Intake

- Current result: ``not_assessed``
- Scenario disposition: ``not_evaluated``
- Versions: v1: Seeded state supported by EVD-0005-001.
- Notes: Non-gating draft intake case used to exercise Not Assessed.

### `ASM-2026-0006` Asset Source Vulnerability Lifecycle

- Current result: ``meets``
- Scenario disposition: ``not_demonstrated``
- Versions: v1: Seeded state supported by EVD-0006-001. / v2: Asset source refresh confirms libfoo 1.4.5 and closes the claim.
- Notes: Continuous-assurance example using asset sources, inventory events, and mitigation traceability.

### `ASM-2026-0007` Command-Link Confidentiality Rehearsal

- Current result: ``meets``
- Scenario disposition: ``plausible``
- Versions: v1: Seeded state supported by EVD-0007-001.
- Notes: Scoped Meets result based on compensating operational controls.

### `ASM-2026-0008` Operational LEO Reset Command Replay

- Current result: ``does_not_meet``
- Scenario disposition: ``demonstrated``
- Versions: v1: Initial event and evidence intake supported by EVD-0008-001–EVD-0008-004. / v2: Final state records execution, telemetry impact, and unresolved transmitter attribution.
- Notes: Operational LEO example combining strong effect evidence with explicit ground-station and attribution gaps.

## Filter expectations

- Portfolio filters should show closed assessments in `meets`, `does_not_meet`, and `inconclusive`.
- The draft intake case should keep a genuine `not_assessed` overall state because its investigation is non-gating.
- Traceability comparisons should be most interesting on the MFA rollout, auth fallback, and asset-source lifecycle cases.

## Suggested demo order

1. `ASM-2026-0001` for a partial mitigation that still fails.
2. `ASM-2026-0002` for a clean mitigation success.
3. `ASM-2026-0003` for a defensible inconclusive result.
4. `ASM-2026-0005` for a true draft intake.
5. `ASM-2026-0006` for asset-source-driven continuous assurance.
6. The operational LEO reset replay case for a demonstrated effect with incomplete source attribution.
