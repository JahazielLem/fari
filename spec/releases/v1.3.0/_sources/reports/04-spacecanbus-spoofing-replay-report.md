# FARI Investigation Report: SpaceCAN Spoofing and Replay

## Document Control

- **Assessment ID:** `ASM-FARI-2026-004`
- **Investigation ID:** `INV-SCAN-001`
- **Report version:** `0.3`
- **Report maturity:** Provisional
- **Report date:** `2026-06-08`
- **Source material:** [`cases/04_Spacecanbus.md`](../cases/04_Spacecanbus.md) and supplied SpaceCAN screenshots
- **Evidence producer:** Auditor; identity not supplied
- **Report author:** FARI Report Author
- **Mission owner / risk authority:** Not supplied
- **Framework profile:** No external framework profile was required for this report.

## 1. FARI Result Card

| Field | Result |
|---|---|
| Conclusion | **Does Not Meet** |
| Confidence | Medium within the lab monitoring scope |
| Required Action | Remediate, then Retest |
| Priority | Immediate before SpaceCAN monitor values are trusted for operational or autonomous decisions |
| Scope Boundary | Supplied SpaceCAN lab injection/replay tools and monitor screenshots; physical subsystem response, flight autonomy, production bus controls, and on-orbit behavior excluded |

**Rationale:** The supplied evidence demonstrates a forged reply-like frame,
replay transmission, and changed displayed telemetry values without evidence
that the displayed data was authenticated, attributed as untrusted, or rejected.
This demonstrates failure of the lab-scope claim. The evidence does not prove
physical actuator effects or mission-level consequence.

## 2. Executive Decision Summary

The SpaceCAN lab monitor accepts or displays bus state that can be influenced by
injected reply-like traffic. A before/after monitor screenshot shows thruster
values changing from `12` to `255` while status remains nominal. The replay
tool also demonstrates retransmission of captured bus frames.

This is sufficient to conclude that the claim fails in the evidenced lab
monitoring scope. It is not sufficient to conclude that physical thrusters,
flight-control logic, or on-orbit systems accepted or acted on the values.

**Decision required:** Do not use unauthenticated SpaceCAN monitor data as a
trusted basis for operational or autonomous action until origin validation,
freshness controls, anomaly handling, and retest evidence are available.

## 3. Frame

### Mission Context Added by the Report Author

The supplied material does not identify a mission architecture or SpaceCAN
consumer. This report uses the explicit assumption that the monitored bus values
could inform operators, health management, or autonomous logic. That assumption
requires mission-owner confirmation.

### Scope

| Item | FARI Record |
|---|---|
| Primary asset | `AST-SCAN-BUS-001` SpaceCAN lab bus |
| Related assets | `AST-SCAN-MON-001` SpaceCAN monitor and `AST-SCAN-NODE-004` represented node `0x04` |
| Segment | Space-segment representative onboard bus lab |
| Access basis | Private, as stated by evidence producer |
| Environment | Dynamic local lab using supplied SpaceCAN examples |
| Claim | `CLM-SCAN-001`: SpaceCAN monitoring and consumers reject or visibly distinguish unauthenticated forged or replayed reply-like frames before treating them as trusted state |
| Explicit exclusions | Physical subsystem behavior, real spacecraft bus controls, autonomous decision logic, RF/ground paths, and on-orbit behavior |

### Authorization

No rules-of-engagement reference, target revision, test date, bus topology,
safety control, or evidence-handling record was supplied.

## 4. Acquire: Source-Material Intake Review

### Evidence Index

| Evidence ID | Source | Directly Supported Statement |
|---|---|---|
| `EVD-SCAN-001` | `spacecan_scinjection_cmd_spoof.png` | The injection tool sent a frame to ID `0x304` with DLC `2` and data `01 FF` |
| `EVD-SCAN-002` | `spacecan_screenplay_replay.png` | The replay tool retransmitted multiple recorded frames, including ID `0x304` |
| `EVD-SCAN-003` | `Spacecan_tui_value_change.png` | The monitor comparison shows thruster values changing from `12` to `255` while status remains nominal |

### Evidence-Backed Facts

- The supplied injection command is
  `./buildDir/examples/scinjection 0x304 01 FF`.
- The injection screenshot shows a sent frame with identifier `0x304`, DLC
  `2`, and data `01 FF`.
- The replay screenshot shows replay activity and multiple frame identifiers,
  including `0x304`.
- The monitor comparison shows values labeled for thrusters changing from `12`
  to `255`; the displayed status remains nominal.

### Evidence-Producer Assertions

- Frame ID `0x304` represents a reply from node `0x04`.
- Monitors or consumers trust reply CAN IDs and attribute the payload to the
  forged node.
- The replay preserves original inter-frame timing.
- No sequence counter, nonce, timestamp authentication, or freshness window
  blocks the replay.
- Forged or replayed traffic can mask subsystem failure or poison higher-level
  decision logic.

### Report-Author Inferences

- The lab monitor displays state that can be influenced by injected bus traffic
  without an evidenced untrusted-data indication.
- The displayed value change is consistent with the supplied injection
  scenario, but the exact chronology and causal capture are not fully
  documented.
- Replay transmission is demonstrated; receiver acceptance and a
  replay-specific state change are not separately isolated.

### Contradictions and Quality Issues

| ID | Issue | Reporting Decision |
|---|---|---|
| `GAP-SCAN-001` | The final finding says the library has DoS in APID `0x06`, which is unrelated to SpaceCAN evidence | Exclude the copied finding statement |
| `GAP-SCAN-002` | The same monitor screenshot is used for spoofing and replay | Confirm displayed-state manipulation in the lab, but keep the replay-specific effect candidate |
| `GAP-SCAN-003` | The exact application meaning of payload `01 FF` is not evidenced | Describe the observed display change without claiming a universal field encoding |
| `GAP-SCAN-004` | No source/configuration evidence demonstrates absence of authentication or freshness controls | Treat missing controls as an evidence request, not an observed fact |
| `GAP-SCAN-005` | Status remains nominal while values change, but alarm semantics are not supplied | Record a possible detection gap without confirming it |

### Sufficiency Decision

| Question | Decision | Rationale |
|---|---|---|
| Technical condition | Sufficient for lab display-trust failure; partial for replay-specific acceptance | Injection/replay actions and displayed value change are evidenced, but replay causality is not isolated |
| External / operational reachability | Partial | Local bus access is demonstrated; production/on-orbit access paths are unknown |
| Mission consequence | Partial | Misleading displayed state is observed; operator, autonomy, and physical effects are not demonstrated |

## 5. Relate: Findings and Mission Context

### FND-SCAN-001: Forged Reply-Like Frame Influences Displayed Telemetry

- **State:** Confirmed within the lab monitor scope
- **Condition:** Reply-like SpaceCAN traffic can be injected using a valid bus
  identifier and displayed without an evidenced untrusted-origin distinction.
- **Observed effect:** The supplied monitor comparison shows displayed thruster
  values changing from `12` to `255` while status remains nominal.
- **Preconditions:** Local bus injection access and a consumer that processes
  the forged identifier and payload.
- **Credible consequence:** Operator or automated logic may use misleading
  state if equivalent behavior exists in the operational system.
- **Technical confidence:** Medium
- **Operational-reachability confidence:** Low
- **Mission-consequence confidence:** Low

### FND-SCAN-002: Captured SpaceCAN Traffic Can Be Replayed

- **State:** Candidate for receiver/control failure; replay transmission
  confirmed
- **Condition:** The supplied replay tool retransmits captured bus frames,
  including ID `0x304`.
- **Observed effect:** Replay transmission is shown; a receiver reaction caused
  specifically by replay is not isolated.
- **Credible consequence:** Stale telemetry or commands may be accepted again
  if operational consumers lack freshness controls.
- **Technical confidence:** Medium for transmission; low for receiver effect.

### Framework Mappings

| Mapping | State | Rationale |
|---|---|---|

### Qualitative Mission Context

> Given local access to the SpaceCAN bus, an actor or faulty node could inject
> or replay reply-like frames that appear as trusted telemetry, potentially
> misleading operators or automated consumers and harming mission decisions.

The displayed-state integrity failure is demonstrated only in the lab scope.
Physical and mission consequences remain provisional.

## 6. Inform

### Required Actions

1. Define which SpaceCAN messages require origin authentication, integrity, and
   freshness protection.
2. Reject or visibly label frames that fail origin, sequence, timing, mode, or
   plausibility checks.
3. Correlate critical telemetry with independent sources and expected state
   transitions.
4. Alert when values change implausibly or conflict with status.
5. Separate monitoring-only data from values allowed to drive control or fault
   management.
6. Retest spoofing and replay against every operational consumer, not only the
   lab display.

### Acceptance Criteria

- Forged reply-like frames are rejected or clearly marked untrusted.
- Previously accepted frames cannot be replayed outside the defined freshness
  window without detection and rejection.
- Critical consumers do not act on unauthenticated or stale state.
- Alerts distinguish inconsistent status and telemetry values.
- Retest evidence covers monitor, control, autonomy, and recovery behavior in a
  representative integration.

### Evidence Gaps and Follow-Up Requests

| Gap ID | Requested Evidence | Why It Matters |
|---|---|---|
| `GAP-SCAN-006` | Timestamped packet capture correlated with the monitor change | Establish exact causality |
| `GAP-SCAN-007` | Bus topology, node ownership, and trust model | Evaluate operational reachability |
| `GAP-SCAN-008` | Receiver/monitor source and security-control configuration | Verify origin and freshness controls |
| `GAP-SCAN-009` | Replay-specific before/after capture | Resolve receiver response to replay |
| `GAP-SCAN-010` | Physical subsystem and autonomous-consumer test results | Evaluate mission consequence |
| `GAP-SCAN-011` | Mission thresholds, alarm semantics, and unacceptable outcomes | Support final mission decision |

### Assurance Statement

> `CLM-SCAN-001` **Does Not Meet** its acceptance criteria with medium
> confidence in the supplied lab monitoring scope. Forged bus traffic and
> changed displayed telemetry are evidenced, and replay transmission is shown.
> No conclusion is made about physical subsystem behavior, autonomous action,
> production controls, or on-orbit consequence.

## 7. Coverage

| Area | Coverage | Result |
|---|---|---|
| Local bus injection | Tested and evidenced | Forged frame transmission shown |
| Lab monitor displayed values | Tested and evidenced | Displayed telemetry changes shown |
| Bus replay transmission | Tested and evidenced | Recorded frames retransmitted |
| Replay-specific receiver effect | Inferred / partial | Not isolated |
| Physical subsystem and autonomy | Not assessed | No conclusion |
| Production and on-orbit environment | Out of scope | No conclusion |

<!-- pagebreak -->

## 8. Closing FARI Result Card

| Field | Result |
|---|---|
| Conclusion | **Does Not Meet** |
| Confidence | Medium within the lab monitoring scope |
| Required Action | Remediate, then Retest |
| Priority | Immediate before displayed SpaceCAN state is trusted for operational decisions |
| Next Decision | Approve trusted use only after origin/freshness controls and representative retest satisfy acceptance criteria |
