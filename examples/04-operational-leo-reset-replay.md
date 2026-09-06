# Example 04 — Operational LEO reset command replay

This example is a complete FARI scenario for an operational satellite command
that was accepted and executed even though it was absent from the approved
operations plan and lacked authentication or replay protection.

The scenario intentionally keeps the evidence boundaries visible:

- operational logs demonstrate receipt, acceptance, execution, and an
  eight-minute telemetry interruption;
- the operations reconciliation leaves all backup-station logs unresolved;
- one RF capture cannot establish the physical transmitter;
- a same-firmware engineering-model reproduction demonstrates repeatability,
  but not flight-vehicle behavior.

Source evidence is in [`cases/05_orbit_reset_replay.md`](../cases/05_orbit_reset_replay.md)
and [`cases/05_evidence/`](../cases/05_evidence/).

Expected FARI result: **Does Not Meet**, **Demonstrated**, medium confidence,
with immediate remediation and retest required.
