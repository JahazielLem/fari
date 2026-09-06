# FARI Investigation Report: USB-Simulated Telecommand Interface

## Document Control

- **Assessment ID:** `ASM-FARI-2026-002`
- **Report version:** `0.2`
- **Report maturity:** Provisional
- **Report date:** `2026-06-07`
- **Source material:** [`cases/02_USB.md`](../cases/02_USB.md)
- **Evidence producer:** Auditor; identity not supplied
- **Report author:** FARI Report Author
- **Mission owner / risk authority:** Not supplied
- **Framework profile:** No external framework profile was required for this report.

## 1. FARI Result Card

| Field | Result |
|---|---|
| Conclusion | **Inconclusive** |
| Confidence | Low |
| Required Action | Extend Investigation |
| Priority | Planned before treating the USB interface as representative of the command path |
| Scope Boundary | Supplied USB test concept, script, assertions, and expected observations; no demonstrated command execution, measured effect, RF equivalence, or on-orbit behavior |

**Rationale:** Relevant analysis and a credible hypothesis exist, but the
supplied material contains no observed execution evidence and includes
contradictory APID and payload descriptions. The claim cannot be resolved as
Meets or Does Not Meet.

## 2. Executive Decision Summary

The supplied case describes a credible configuration-logic weakness: a
`SET_BEACON_RATE` command may accept a zero-second interval, causing beacon
generation to execute nearly continuously and potentially degrading telemetry
visibility or other mission-loop functions.

The supplied source material does not include execution output, command
acknowledgements, traffic captures, measured rate changes, source references, or
recovery observations. It also contains an unresolved APID contradiction.
Therefore, the weakness and mission effect are reported as **candidate**, not
confirmed.

**Decision required:** Run a controlled, instrumented reproduction after
resolving the APID and payload-format contradictions. Independently of the
result, reject zero and unsafe beacon intervals in firmware before using the
interface as a representative RF-path simulation.

## 3. Frame

### Mission Context Added by the Report Author

The supplied source material does not identify a mission or architecture. For analysis,
this report uses the following explicit assumptions:

- The USB-connected target is a FlatSat, engineering model, or representative
  spacecraft processor.
- Beacon telemetry shares processing, buffering, or link resources with normal
  mission telemetry.
- Maintaining readable, timely telemetry is a mission objective.

These assumptions require mission-owner confirmation.

### Scope

| Item | FARI Record |
|---|---|
| Primary asset | `AST-USB-TC-001` USB-exposed telecommand interface |
| Related asset | `AST-FSW-BEACON-001` Beacon-rate command handler and telemetry worker |
| Segment | Space segment representative environment and simulated link |
| Access basis | Private, as stated by evidence producer |
| Environment | USB serial at `921600` baud; dynamic lab execution claimed |
| Claim | `CLM-USB-001`: Configuration commands reject values that can cause uncontrolled telemetry generation or mission-loop degradation |
| Explicit exclusions | Actual RF transmission, on-orbit behavior, authentication path, full mission-loop resource analysis |

### Authorization

The case instructs use only during a controlled lab window, but no authorization
record, stop condition, target revision, test date, or evidence-handling record
was supplied.

## 4. Acquire: Source-Material Intake Review

### Evidence-Backed Facts

- The supplied Python example constructs a CCSDS space-packet telecommand with
  `apid=6`, `seq_count=5`, and `data_len=0`.
- The example sends the packed header plus a newline to
  `/dev/cu.usbmodemfsat3` at `921600` baud.
- The execution narrative identifies target APID `0x05` and command
  `SET_BEACON_RATE`.
- The narrative defines a two-byte lab payload: interval plus padding.
- The narrative provides commands intended to send one-second, zero-second, and
  recovery intervals using `scripts/usb_tc_send.py`.
- The case contains expected observations but no recorded observations or
  command output.

### Evidence-Producer Assertions

- USB is used to simulate the RF channel.
- The handler reads `data[0]`, rejects values above `10`, and accepts `0`.
- A zero interval makes the telemetry-worker condition true almost
  continuously.
- The result is a logic-level denial of service against the mission loop.

### Report-Author Inferences

- If the handler and scheduling condition behave as described, accepting zero
  can create uncontrolled beacon generation.
- Uncontrolled beacon generation may consume processing or link capacity and
  reduce operator telemetry visibility.
- The provided case is a test plan and technical hypothesis rather than a
  completed execution record.

### Contradictions and Quality Issues

| ID | Issue | Reporting Decision |
|---|---|---|
| `GAP-USB-001` | Python example uses APID decimal `6`; execution narrative identifies APID `0x05` (decimal `5`) | Finding remains candidate until the correct APID is demonstrated |
| `GAP-USB-002` | Python example sends only a packed SPP header, while the reproduction requires interval and padding bytes | Require exact transmitted bytes and command acknowledgement |
| `GAP-USB-003` | Case declares static/offline and dynamic environments without identifying which evidence came from each | Report treats environment as an incompletely documented dynamic lab |
| `GAP-USB-004` | Final finding text refers to a library DoS in several packets, which does not match this USB beacon-rate scenario | Report excludes the copied finding statement |
| `GAP-USB-005` | Proposed `EX-0005.01` mapping is not the strongest match for the described software logic condition | Report uses candidate mappings to command packets, flight-software code flaws, and inhibited spacecraft functionality |

### Sufficiency Decision

| Question | Decision | Rationale |
|---|---|---|
| Technical condition | Partial | Detailed producer assertion exists, but no source reference or observed execution output |
| External / operational reachability | Insufficient | USB delivery is described but not evidenced; RF equivalence and authentication are unknown |
| Mission consequence | Insufficient | Only expected effects are supplied; no measured degradation or recovery evidence |

## 5. Relate: Candidate Finding and Mission Context

### FND-USB-001: Zero Beacon Interval May Cause Uncontrolled Telemetry Generation

- **State:** Candidate
- **Condition:** The `SET_BEACON_RATE` handler is asserted to accept zero even
  though zero causes the scheduling condition to run nearly continuously.
- **Observed effect:** None supplied.
- **Expected effect:** Repeated beacon telemetry, increased USB/downlink traffic,
  and reduced readability of normal telemetry.
- **Preconditions:** Correct command APID and payload reach the handler; command
  is accepted; no upstream validation or authorization control rejects it.
- **Credible mission consequence:** Degraded telemetry visibility or
  mission-loop availability.
- **Technical confidence:** Low
- **Reachability confidence:** Low
- **Mission-consequence confidence:** Low

### Framework Mappings

| Mapping | State | Rationale |
|---|---|---|

### Qualitative Mission Context

> Given command-path access, an actor or erroneous operator procedure could set
> the beacon interval to zero, potentially causing uncontrolled telemetry
> generation and degrading mission telemetry visibility or mission-loop
> availability.

The scenario could become operationally important if RF delivery is possible
without strong command authentication, if zero persists across reset, or if
beacon flooding interferes with command reception or safing. Those conditions
were not demonstrated, so the appropriate executive result is to extend the
investigation rather than assign a numeric risk value.

## 6. Inform

### Required Controlled Reproduction

1. Confirm the intended APID and exact command identifier from the command
   dictionary.
2. Record the exact transmitted bytes for baseline, one-second, zero-second,
   and recovery commands.
3. Capture command acknowledgement or handler instrumentation proving command
   acceptance.
4. Measure baseline and test beacon rates, USB/link utilization, CPU usage,
   queue depth, dropped telemetry, and command responsiveness.
5. Record behavior during zero interval and recovery using predefined stop
   conditions.
6. Repeat after implementing validation that rejects zero and values outside an
   approved operational range.

### Required Remediation

- Reject zero and unsafe beacon intervals before updating scheduler state.
- Define a mission-approved minimum and maximum interval.
- Use safe defaults when values are invalid or missing.
- Add command-level authorization and mode restrictions where appropriate.
- Rate-limit telemetry generation independently of configuration input.
- Alert operators when beacon rate changes or exceeds expected bounds.

### Acceptance Criteria

- Zero and all out-of-range values are rejected with an explicit error.
- Rejected commands do not change the active interval.
- Beacon generation remains within the mission-approved rate under malformed,
  repeated, or unauthorized inputs.
- Normal telemetry and command responsiveness remain within defined thresholds.
- Recovery behavior is measured and documented.

### Evidence Gaps and Follow-Up Requests

| Gap ID | Requested Evidence | Why It Matters |
|---|---|---|
| `GAP-USB-006` | Correct APID, command dictionary entry, and exact wire bytes | Resolve contradictory targeting information |
| `GAP-USB-007` | Source reference for handler validation and scheduling condition | Confirm technical condition |
| `GAP-USB-008` | Execution logs, command acknowledgement, and traffic capture | Confirm command delivery and observed effect |
| `GAP-USB-009` | Baseline/test measurements and recovery observations | Quantify mission consequence |
| `GAP-USB-010` | Firmware revision, hardware revision, tool versions, and evidence hashes | Reproducibility |
| `GAP-USB-011` | RF-equivalence rationale and command-authentication controls | Evaluate operational reachability |
| `GAP-USB-012` | Mission telemetry thresholds and unacceptable outcomes | Final risk decision |

### Assurance Statement

> `CLM-USB-001` is **Inconclusive** with low confidence. The supplied case
> describes a credible unsafe configuration condition, but it does not contain
> observed execution evidence.
> No conclusion is made about RF reachability, authentication bypass, measured
> mission degradation, persistence, or on-orbit behavior.

## 7. Coverage

| Area | Coverage | Result |
|---|---|---|
| USB delivery concept | Reviewed | Script and procedure supplied; execution not evidenced |
| Beacon-rate handler logic | Inferred | Producer assertions supplied; source reference absent |
| Zero-interval behavior | Not assessed by supplied evidence | Expected observations only |
| Recovery | Not assessed by supplied evidence | Proposed procedure only |
| RF equivalence | Not assessed | No evidence supplied |
| On-orbit behavior | Out of scope | No evidence supplied |

<!-- pagebreak -->

## 8. Closing FARI Result Card

| Field | Result |
|---|---|
| Conclusion | **Inconclusive** |
| Confidence | Low |
| Required Action | Extend Investigation |
| Priority | Planned before representative-command-path acceptance |
| Next Decision | Resolve the claim after controlled execution captures the exact command, observed behavior, and recovery |
