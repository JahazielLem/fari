# Scenario 05 — LEO operational reset command replay

## Purpose

This scenario exercises a FARI investigation where an unauthenticated command
was accepted and executed during an operational contact window, while the
physical origin of the transmitter and the complete ground-station record
remain unresolved.

## Event

The event occurred on **2026-05-14 at 10:01:30 UTC** during a scheduled contact
window with an operational satellite in low Earth orbit.

A ground station captured an RF frame with valid CCSDS structure. The APID
corresponds to the flight-computer reset command. The frame contains no
cryptographic authentication mechanism and no replay protection.

Satellite logs show that the command was received, accepted, and executed. The
reset counter increased and telemetry was interrupted for eight minutes.

The command is absent from the approved operations plan and from the primary
ground station transmission records. Records from all backup stations were not
provided, and a single RF capture cannot identify the physical transmitter.

In a laboratory, the same frame structure repeatedly caused a reset using the
same firmware, an engineering model, and not the flight vehicle.

## FARI claim

> The operational command path rejects unauthenticated or replayed reset
> commands and preserves sufficient attribution to distinguish authorized
> commanding from an injected transmission.

## Expected result

- **Conclusion:** Does Not Meet
- **Scenario disposition:** Demonstrated
- **Confidence:** Medium
- **Required action:** Remediate, then retest
- **Priority:** Immediate

The operational execution and eight-minute telemetry interruption support the
claim failure. The missing backup-station records and the lack of physical
transmitter attribution remain explicit evidence gaps. The laboratory result
supports repeatability but does not independently prove flight-vehicle behavior.

## Evidence package

- `05_evidence/01-contact-window-rf-capture.txt`
- `05_evidence/02-satellite-execution-log.txt`
- `05_evidence/03-operations-reconciliation-and-gaps.txt`
- `05_evidence/04-lab-repeatability-report.txt`

These files are also generated into the seeded web workspace as evidence linked
to the example investigation.
