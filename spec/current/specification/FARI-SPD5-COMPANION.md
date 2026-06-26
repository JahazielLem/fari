# FARI SPD-5 Companion Profile

**Companion profile for FARI v1.2.0**

## Purpose

This document defines a control-oriented overlay that can be used alongside
FARI when an assessment also needs to support SPD-5-style compliance
conversations.

FARI remains the core evidence and executive reporting framework.

The SPD-5 companion profile is:

- optional;
- qualitative;
- traceable back to FARI records;
- useful for executive readiness and gap-review conversations;
- not a certification, legal determination, or replacement for authority review.

## Why a companion instead of changing FARI

FARI is built around claims, evidence normalization, scope boundaries, findings,
SPARTA mappings, and executive conclusions.

SPD-5 is a principle set for space-system cybersecurity. It is better used as a
control overlay than as the engine that drives every FARI decision.

That separation keeps both sides clean:

- FARI answers: *what was tested and what can be concluded?*
- the SPD-5 companion answers: *how does that evidence align with a known
  cybersecurity baseline?*

## Source reference

- [Official SPD-5 PDF](https://www.transportation.gov/sites/dot.gov/files/2023-11/Memorandum%20on%20Space%20Policy%20Directive-5%E2%80%94Cybersecurity%20Principles%20for%20Space%20Systems.pdf)
- [DOT reference page](https://www.transportation.gov/pnt/memorandum-space-policy-directive-5-cybersecurity-principles-space-systems)

## Recommended usage model

Use the companion profile at the **assessment** level, not as a replacement for
individual investigations.

Each companion control should reference one or more existing FARI records, for
example:

- investigation IDs;
- evidence IDs;
- asset IDs;
- SPARTA-linked findings;
- Attack Flow diagrams;
- SBOM documents;
- inventory component timelines.

## Compliance proceeding scenarios

These scenarios describe how a compliance-oriented assessment may proceed.

### 1. Evidence-backed alignment

Use when the relevant control exists and FARI has enough evidence to support
that statement directly.

Typical pattern:

- control status mostly `Implemented`;
- evidence references are concrete;
- no material scope caveat remains.

### 2. Partial alignment

Use when the mission has meaningful control coverage, but some items are only
partially implemented or still planned.

Typical pattern:

- a mix of `Implemented`, `Partially Implemented`, and `Planned`;
- gaps are known;
- the profile still helps prioritize work.

### 3. Compensating controls

Use when the expected control does not exist in its standard form, but another
design choice reduces the same exposure.

Typical pattern:

- a direct control is absent;
- rationale explains why the alternative is acceptable;
- linked evidence shows the compensating behavior.

### 4. Inconclusive due to scope

Use when the current assessment cannot support a dependable compliance
statement.

Typical pattern:

- limited environment or access;
- supplier black-box constraints;
- missing mission or operational evidence;
- many controls still `Not Verified`.

### 5. Supplier attestation pending

Use when third-party firmware, cloud services, or other external dependencies
must provide additional evidence before the control can be accepted.

Typical pattern:

- vendor claim exists but local validation is missing;
- supply-chain or hosted-service controls remain open;
- the profile tracks what must still be obtained.

### 6. Continuous assurance

Use when the assessment becomes a living baseline and is revisited over time.

Typical pattern:

- SBOM imports change;
- monitoring coverage grows;
- fixes are retested;
- captured revisions document each state change.

## Control status model

Each control uses one of these values:

- `Implemented`
- `Partially Implemented`
- `Planned`
- `Not Implemented`
- `Not Applicable`
- `Not Verified`

Recommended interpretation:

- `Implemented`: supported by current evidence.
- `Partially Implemented`: some evidence exists, but not enough for a clean
  implementation statement.
- `Planned`: known remediation or project exists, but the control is not yet in
  force.
- `Not Implemented`: the control is absent or effectively not present.
- `Not Applicable`: the control does not belong to the declared scope.
- `Not Verified`: the control may exist, but the present assessment cannot
  support that statement.

## Companion posture model

The profile can roll up into a qualitative posture:

- `Aligned`
- `Partially Aligned`
- `Gap Identified`
- `Inconclusive`
- `Not Started`

Recommended interpretation:

- `Aligned`: applicable controls are implemented.
- `Partially Aligned`: some controls are implemented, but others are only
  partial or planned.
- `Gap Identified`: one or more applicable controls are clearly absent.
- `Inconclusive`: the profile is active, but evidence is still too incomplete
  for a stronger statement.
- `Not Started`: the profile has not yet moved beyond unverified controls.

## Control families

### Governance

- `SPD5-GOV-01` Space system cybersecurity policy
- `SPD5-GOV-02` Threat analysis performed
- `SPD5-GOV-03` SPARTA threat model completed
- `SPD5-GOV-04` Incident response procedures

### Ground Segment

- `SPD5-GRD-01` MFA for operators
- `SPD5-GRD-02` RBAC implemented
- `SPD5-GRD-03` Command logging and auditability
- `SPD5-GRD-04` SIEM integration
- `SPD5-GRD-05` Network segmentation

### Space Segment

- `SPD5-SPC-01` Authenticated telecommands
- `SPD5-SPC-02` Encrypted telecommands
- `SPD5-SPC-03` Firmware integrity validation
- `SPD5-SPC-04` Secure boot
- `SPD5-SPC-05` Positive control recovery
- `SPD5-SPC-06` Safe mode documented

### Communications

- `SPD5-COM-01` Replay protection
- `SPD5-COM-02` Spoofing protection
- `SPD5-COM-03` Cryptographic key management
- `SPD5-COM-04` Credential rotation
- `SPD5-COM-05` RF link protection

### Supply Chain

- `SPD5-SUP-01` Software inventory (SBOM)
- `SPD5-SUP-02` Third-party firmware validation
- `SPD5-SUP-03` Change control
- `SPD5-SUP-04` Signed updates

### Monitoring

- `SPD5-MON-01` RF anomaly detection
- `SPD5-MON-02` Telemetry monitoring
- `SPD5-MON-03` Critical event alerting
- `SPD5-MON-04` Post-incident forensic capability

## Manual workflow

1. Complete the normal FARI Frame.
2. Register assets, investigations, evidence, findings, SPARTA links, and any
   Attack Flow material.
3. If software composition matters, ingest SBOM material and inventory events.
4. Open the SPD-5 companion profile.
5. Select the current compliance proceeding scenario.
6. For each control, choose a qualitative status.
7. Add evidence references pointing back to existing FARI records.
8. Add notes for scope limits, compensating controls, or supplier dependencies.
9. Review the resulting posture as an executive signal, not as a legal
   certification.

## Web implementation guidance

The web interface should treat the SPD-5 companion as:

- an assessment-level module;
- optional for closure;
- revision-aware through the assessment snapshot system;
- exportable in JSON;
- readable in a future consolidated governance appendix if needed.

## Minimal worked example

Assessment:

- `ASM-2026-0001`
- SpaceCAN replay-resistance review

FARI evidence:

- `INV-0001-001`
- `EVD-0001-001`
- `FND-0001-001`
- `AFB-0001-001`

Companion interpretation:

- `SPD5-COM-01 Replay protection` -> `Not Implemented`
- `SPD5-COM-02 Spoofing protection` -> `Partially Implemented`
- `SPD5-GOV-02 Threat analysis performed` -> `Implemented`

Possible posture:

- `Gap Identified`

Possible scenario:

- `Partial alignment`

Reason:

- some governance work exists;
- communication-path defenses are incomplete;
- evidence supports a concrete remediation conversation.
