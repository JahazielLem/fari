# FARI Manual Assessment Template

Use this template when FARI is filled manually outside the web application. The
sections and field names match the current workflow in the application.

## Document control

- Generated with: `FARI v1.3.0`
- Assessment ID: `[ASM-YYYY-NNNN]`
- Investigation ID: `[INV-YYYY-NNNN or local reference]`
- Claim ID: `[CLM-YYYY-NNNN or local reference]`
- Revision label: `[v0, v1, v2 ...]`
- Report author: `Fari-Agent`
- Technical reporter: `[name or team]`
- Report state: `[draft | closed]`
- Report maturity: `[draft | provisional | final | superseded]`

## 1. Frame

- Client name: `[client]`
- Assessment title: `[assessment title]`
- Mission context: `[short mission or operational context]`
- Scope: `[exact assessment boundary]`
- Authorization: `[authorization or engagement reference]`
- Exclusions: `[what is explicitly out of scope]`

### Asset

- Asset ID: `[AST-...]`
- Asset name: `[name]`
- Segment: `[space | ground | user | link | supply_chain | cloud | other]`
- Access basis: `[public | private | other]`
- Coverage: `[tested | reviewed | inferred | not_assessed | out_of_scope]`
- Description: `[what this asset is]`

### Claim

- Claim description: `[expected secure behavior being evaluated]`
- Gating claim: `[yes | no]`

## 2. Acquire

### Supplied material and evidence

- Evidence reference 1: `[file, note, screenshot, capture, script, report]`
- Evidence reference 2: `[optional]`
- Evidence reference 3: `[optional]`

### Normalized material

#### Facts

- `[fact directly supported by evidence]`
- `[fact directly supported by evidence]`

#### Assertions

- `[statement supplied by the technical reporter]`

#### Inferences

- `[report-author interpretation]`

#### Assumptions

- `[assumption used for current analysis]`

#### Contradictions

- `[material conflict affecting confidence or conclusion]`

#### Gaps

- `[missing information that blocks a stronger conclusion]`

### Sufficiency

- Technical sufficiency: `[sufficient | partial | insufficient]`
- Reachability sufficiency: `[sufficient | partial | insufficient]`
- Mission sufficiency: `[sufficient | partial | insufficient]`

### Optional asset source inventory

- Asset source ID: `[SRC-...]`
- Related asset: `[AST-...]`
- Filename and format: `[firmware.bin | capture.sigmf-meta | capture.pcap | dependency.json | ...]`
- Detected format: `[cyclonedx | spdx | jsonl | sigmf-meta | sigmf-data | binary | pcap | pcapng | text | ...]`
- SHA-256: `[...]`
- Intake result: `[components normalized | raw source preserved]`
- Component ID: `[CMP-...]`
- Component name: `[package or library]`
- Current version: `[version]`
- Inventory status: `[tracked | vulnerable | update_in_progress | fixed | accepted | not_affected]`
- Inventory event: `[imported | vulnerability_detected | version_updated | fix_verified | status_changed | note]`
- Event summary: `[what changed and why]`

## 3. Relate

### Finding

- Finding ID: `[FND-...]`
- Title: `[concise reportable condition]`
- State: `[observation | candidate | confirmed | remediated | verified_closed]`
- Condition text: `[what is wrong or notable]`
- Observed effect: `[what was directly observed]`
- Credible impact: `[why this matters]`

### Framework mapping

- Framework: `[optional external framework]`
- External identifier: `[optional]`
- External name: `[optional]`
- Mapping state: `[confirmed | candidate | not_applicable]`
- Mapping rationale: `[why the mapping is appropriate]`

## 4. Inform

- Conclusion: `[meets | does_not_meet | inconclusive | not_assessed]`
- Scenario disposition: `[demonstrated | plausible | not_demonstrated | not_evaluated]`
- Confidence: `[high | medium | low]`
- Required action: `[accept | remediate | extend_investigation | retest | no_action]`
- Priority: `[immediate | planned | routine | none]`
- Scope boundary: `[exact limit of the conclusion]`
- Rationale: `[short evidence-based reason for the conclusion]`

### Recommendations

- `[recommended next action]`
- `[recommended next action]`

### Acceptance criteria

- `[what evidence would allow closure or validation]`
- `[what evidence would allow closure or validation]`

## 5. Closure check

- [ ] Frame is complete and specific.
- [ ] Evidence or normalized supplied material is present.
- [ ] Facts, assertions, and inferences are separated.
- [ ] Scenario disposition is selected.
- [ ] Conclusion and required action are compatible.
- [ ] Asset sources and inventory state are updated when relevant to the scope.
- [ ] A revision was captured if the assessment meaning changed materially.
- [ ] Scope boundary and rationale are written.
- [ ] Record is understandable without re-explaining the engagement verbally.

## 6. Simple example

- Client name: `Example Aerospace`
- Assessment title: `SpaceCAN Monitor Validation`
- Claim description: `The monitor distinguishes forged reply-like frames before presenting trusted state.`
- Facts:
  - `Forged traffic was transmitted.`
  - `The displayed value changed from 12 to 255.`
- Technical sufficiency: `sufficient`
- Reachability sufficiency: `partial`
- Mission sufficiency: `partial`
- Finding title: `Forged reply-like frame influences displayed telemetry`
- Framework mapping: `[optional external reference]`
- Conclusion: `does_not_meet`
- Scenario disposition: `plausible`
- Required action: `remediate`
- Scope boundary: `Lab monitor path only; physical and on-orbit effects excluded.`
- Rationale: `The tested display accepted attacker-controlled traffic as trusted state.`
