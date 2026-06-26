# FARI Scenario Test Catalog

Seeded workspace catalog for the local FARI demo database.

The workspace was reset and repopulated to cover the main FARI claim outcomes,
scenario dispositions, mitigation traces, and SPD-5 companion-profile modes.

## Coverage summary

- `Does Not Meet`: present in current state and in initial mitigation snapshots.
- `Meets`: present in clean success, mitigation-success, and compensating-control cases.
- `Inconclusive`: present as a closed replay-characterization case.
- `Not Assessed`: present as a draft non-gating intake case.
- `Demonstrated`, `Plausible`, `Not Demonstrated`, and `Not Evaluated` are all represented.
- Every seeded case includes an SPD-5 companion profile.

## Assessments

| Assessment | Current result | Scenario disposition | SPD-5 companion | Posture | Versions | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ASM-2026-0001` Command Auth Fallback Review | `does_not_meet` | `demonstrated` | `Partial alignment` | `partially_aligned` | v1: Initial confirmed bypass on the legacy bridge.<br>v2: RF path fixed, residual maintenance bridge keeps the finding open. | Covers a realistic partial mitigation where the executive result remains Does Not Meet. |
| `ASM-2026-0002` Privileged Operator MFA Rollout | `meets` | `not_demonstrated` | `Evidence-backed alignment` | `aligned` | v1: Password-only privileged access confirmed.<br>v2: MFA enforced and retested successfully. | Canonical mitigation example that ends in Meets with a clear audit trail. |
| `ASM-2026-0003` Replay Window Characterization | `inconclusive` | `plausible` | `Inconclusive due to scope` | `inconclusive` | v1: Short-window replay retest only; full freshness coverage still pending. | Reference case for Inconclusive plus Plausible and an inconclusive SPD-5 overlay. |
| `ASM-2026-0004` Telemetry API RBAC Review | `meets` | `not_demonstrated` | `Evidence-backed alignment` | `aligned` | v1: RBAC and audit controls confirmed on the telemetry API path. | Primary cloud reference for a clean success case. |
| `ASM-2026-0005` Third-Party Firmware Intake | `not_assessed` | `not_evaluated` | `Supplier attestation pending` | `inconclusive` | v1: Intake-only snapshot with a real Not Assessed outcome. | Non-gating draft case used to exercise the Not Assessed portfolio state and supplier-pending overlay. |
| `ASM-2026-0006` SBOM Vulnerability Lifecycle | `meets` | `not_demonstrated` | `Continuous assurance` | `aligned` | v1: Baseline image contains libfoo 1.4.2 with an open advisory.<br>v2: SBOM refresh confirms libfoo 1.4.5 and closes the claim. | Primary continuous-assurance example using SBOM, inventory events, and mitigation traceability. |
| `ASM-2026-0007` Command-Link Confidentiality Rehearsal | `meets` | `plausible` | `Compensating controls` | `aligned` | v1: Scoped confidentiality result based on compensating controls. | Reference case for Meets plus Plausible and the compensating-controls companion scenario. |

## Filter expectations

- Portfolio filters should show closed assessments in `meets`, `does_not_meet`, and `inconclusive`.
- The draft intake case should keep a genuine `not_assessed` overall state because its investigation is non-gating.
- Traceability comparisons should be most interesting on the MFA rollout, auth fallback, and SBOM lifecycle cases.

## Suggested demo order

1. `ASM-2026-0001` for a partial mitigation that still fails.
2. `ASM-2026-0002` for a clean mitigation success.
3. `ASM-2026-0003` for a defensible inconclusive result.
4. `ASM-2026-0005` for a true draft intake and supplier-pending view.
5. `ASM-2026-0006` for SBOM-driven continuous assurance.
