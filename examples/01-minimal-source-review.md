# Example 1: Minimal Source Review

## Scenario

A supplier provides source code for a telemetry parsing library, build
instructions, and unit tests. No target hardware, full flight image, RF
interface, or mission architecture is available.

## Frame

- **Assessment:** `ASM-2026-001`
- **Asset:** `AST-SV-LIB-001` Telemetry parsing library
- **Segment:** Space
- **Access:** White box
- **Environment:** Static/offline analysis
- **Claim `CLM-001`:** Malformed packet lengths cannot cause the library to
  write outside its destination buffer.
- **Explicit exclusions:** Runtime integration, compiler hardening, hardware
  behavior, RF reachability, and mission consequence validation.

## Acquire

`RUN-SRC-001` uses the assessor's preferred secure-code-review method. It finds
that a packet-controlled length is copied into a fixed-size destination without
an upper-bound check.

Evidence:

- `EVD-001`: source reference and annotated data flow.
- `EVD-002`: unit-test case demonstrating overwrite under a host build.

## Relate

### Normalized Finding

- **Finding:** `FND-001` Unbounded telemetry frame length permits memory
  corruption.
- **State:** Confirmed.
- **Observed effect:** Memory overwrite in a host unit-test build.
- **SPARTA candidate:** `EX-0009 Exploit Code Flaws`.
- **Mapping state:** Candidate, because spacecraft execution and effect were not
  demonstrated.
- **Risk:** High-consequence potential, but likelihood and actual mission
  consequence cannot be confidently established without integration context.
- **Confidence:** High for the code defect; low for mission consequence.

## Inform

### FARI Result Card

| Field | Result |
|---|---|
| Conclusion | Does Not Meet |
| Confidence | High in the reviewed source and host unit-test scope |
| Required Action | Remediate, then Retest |
| Priority | Immediate before integration approval |
| Scope Boundary | Telemetry parsing library source and supplied host tests only |

### Recommendation

Add explicit bounds validation, negative tests, and sanitizer-enabled CI.
Verify the fix in the integrated flight-software build and a representative
runtime environment.

### Assurance Statement

> Claim CLM-001 is not supported. The source and host unit-test evidence
> confirms a memory-safety defect with high confidence. No conclusion is made
> about RF exploitability, target-hardware behavior, or mission impact.

### Why this is useful

FARI prevents a narrow source review from being over-reported as a complete
spacecraft vulnerability while still preserving a clear, actionable result.
