"""Reset the local FARI workspace and seed representative assessment cases."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from webapp.db import (  # noqa: E402
    Assessment,
    Asset,
    Evidence,
    Finding,
    Investigation,
    InventoryComponent,
    InventoryEvent,
    AssetSource,
    db,
    init_app as init_db,
    next_sequence,
)
from webapp.reporting import overall_conclusion  # noqa: E402
from webapp.traceability import capture_assessment_version  # noqa: E402


INSTANCE_DIR = Path(os.environ.get("FARI_DATA_DIR", PROJECT_ROOT / "instance"))
EVIDENCE_DIR = INSTANCE_DIR / "evidence"
SOURCE_DIR = INSTANCE_DIR / "sources"
DATABASE_PATH = INSTANCE_DIR / "fari.sqlite3"
CATALOG_PATH = PROJECT_ROOT / "spec" / "current" / "reports" / "FARI-SCENARIO-TEST-CATALOG.md"
ORBIT_RESET_EVIDENCE_DIR = PROJECT_ROOT / "cases" / "05_evidence"
BASE_TIME = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


@dataclass
class SeedCase:
    assessment: Assessment
    investigation: Investigation | None
    current_result: str
    current_scenario: str
    versions: list[tuple[str, str]]
    notes: str


class Clock:
    def __init__(self, start: datetime):
        self.current = start

    def tick(self, minutes: int = 17) -> str:
        stamp = self.current
        self.current += timedelta(minutes=minutes)
        return stamp.replace(microsecond=0).isoformat()


def configured_database_url() -> str | None:
    url = os.environ.get("FARI_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        return None
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def reset_workspace() -> None:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    for path in (EVIDENCE_DIR, SOURCE_DIR):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    if not configured_database_url() and DATABASE_PATH.exists():
        DATABASE_PATH.unlink()


def make_app() -> Flask:
    app = Flask(__name__)
    database_url = configured_database_url()
    app.config.update(
        SECRET_KEY="fari-seed",
        DATABASE=str(DATABASE_PATH),
        UPLOAD_DIR=str(EVIDENCE_DIR),
        ASSET_SOURCE_DIR=str(SOURCE_DIR),
        SQLALCHEMY_DATABASE_URI=database_url or "sqlite:///" + str(DATABASE_PATH),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    init_db(app)
    return app


def reset_database_schema() -> None:
    """Reset current and legacy tables before rebuilding the seeded workspace."""
    if db.engine.dialect.name == "postgresql":
        # The current metadata intentionally no longer includes removed modules.
        # Dropping the public schema also removes legacy tables and their FKs.
        with db.engine.begin() as connection:
            connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
            connection.exec_driver_sql("CREATE SCHEMA public")
    else:
        db.drop_all()
    db.create_all()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, payload: dict) -> bytes:
    raw = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def create_assessment(clock: Clock, *, title: str, client: str, context: str, scope: str, authorization: str, exclusions: str, status: str = "closed", maturity: str = "final") -> Assessment:
    assessment = Assessment(
        client_name=client,
        title=title,
        mission_context=context,
        scope=scope,
        authorization=authorization,
        exclusions=exclusions,
        status=status,
        maturity=maturity,
        report_author="Fari-Agent",
        created_at=clock.tick(),
        updated_at=clock.tick(),
    )
    db.session.add(assessment)
    db.session.flush()
    assessment.fari_id = f"ASM-2026-{assessment.id:04d}"
    return assessment


def add_asset(clock: Clock, assessment: Assessment, *, name: str, segment: str, description: str, access_model: str = "private", coverage: str = "tested") -> Asset:
    asset = Asset(
        assessment=assessment,
        fari_id=f"AST-{assessment.id:04d}-{next_sequence(assessment.assets, 'AST'):03d}",
        name=name,
        segment=segment,
        description=description,
        access_model=access_model,
        coverage=coverage,
        created_at=clock.tick(),
    )
    db.session.add(asset)
    db.session.flush()
    assessment.updated_at = clock.tick()
    return asset


def add_investigation(clock: Clock, assessment: Assessment, asset: Asset | None, *, title: str, claim: str, gating: bool, result: str, scenario: str, action: str, priority: str = "planned", method: str = "Controlled validation and review.", facts: str = "The supplied evidence was reviewed within the declared scope.", inferences: str = "The observed behavior is limited to the tested boundary.", gaps: str = "No additional gaps were recorded for the seeded case.", rationale: str = "The selected result is supported by the seeded evidence and declared boundary.", status: str = "closed") -> Investigation:
    sequence = next_sequence(assessment.investigations, "INV")
    investigation = Investigation(
        assessment=assessment,
        asset=asset,
        fari_id=f"INV-{assessment.id:04d}-{sequence:03d}",
        claim_id=f"CLM-{assessment.id:04d}-{sequence:03d}",
        title=title,
        claim_description=claim,
        gating=gating,
        technical_reporter="FARI validation team",
        method=method,
        environment="Seeded local validation workspace.",
        facts=facts,
        assertions="The seeded source is representative of the declared test boundary.",
        inferences=inferences,
        assumptions="The declared authorization and test conditions remain valid.",
        contradictions="None observed in the seeded material.",
        gaps=gaps,
        technical_sufficiency="sufficient" if result in {"meets", "does_not_meet"} else "partial",
        reachability_sufficiency="sufficient" if result in {"meets", "does_not_meet"} else "partial",
        mission_sufficiency="partial",
        conclusion=result,
        scenario_state=scenario,
        confidence="high" if result in {"meets", "does_not_meet"} else "medium",
        required_action=action,
        priority=priority,
        scope_boundary="Conclusion applies only to the declared seeded validation boundary.",
        rationale=rationale,
        recommendations="Repeat the validation after material system changes.",
        acceptance_criteria="A follow-up run preserves the selected result or records a new evidence-backed conclusion.",
        status=status,
        created_at=clock.tick(),
        updated_at=clock.tick(),
    )
    db.session.add(investigation)
    db.session.flush()
    assessment.updated_at = clock.tick()
    return investigation


def add_evidence(clock: Clock, investigation: Investigation, *, filename: str, description: str, body: str) -> Evidence:
    sequence = next_sequence(investigation.evidence, "EVD")
    fari_id = f"EVD-{investigation.id:04d}-{sequence:03d}"
    stored_name = f"{fari_id}-{filename}"
    raw = body.strip().encode("utf-8") + b"\n"
    target = EVIDENCE_DIR / investigation.fari_id / stored_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    evidence = Evidence(
        investigation=investigation,
        fari_id=fari_id,
        filename=filename,
        stored_name=stored_name,
        description=description,
        sha256=sha256_bytes(raw),
        mime_type="text/plain",
        uploaded_at=clock.tick(),
    )
    db.session.add(evidence)
    db.session.flush()
    investigation.updated_at = clock.tick()
    investigation.assessment.updated_at = clock.tick()
    return evidence


def add_finding(clock: Clock, investigation: Investigation, *, title: str, state: str, condition: str, effect: str, impact: str, mapping_state: str = "candidate", mapping_rationale: str = "") -> Finding:
    finding = Finding(
        investigation=investigation,
        fari_id=f"FND-{investigation.id:04d}-{next_sequence(investigation.findings, 'FND'):03d}",
        title=title,
        state=state,
        condition_text=condition,
        observed_effect=effect,
        credible_impact=impact,
        mapping_state=mapping_state,
        mapping_rationale=mapping_rationale,
        created_at=clock.tick(),
    )
    db.session.add(finding)
    db.session.flush()
    investigation.updated_at = clock.tick()
    investigation.assessment.updated_at = clock.tick()
    return finding


def add_asset_source(clock: Clock, assessment: Assessment, asset: Asset, *, filename: str, payload: dict, notes: str) -> AssetSource:
    fari_id = f"SRC-{assessment.id:04d}-{next_sequence(asset.sources, 'SRC'):03d}"
    stored_name = f"{fari_id}-{filename}"
    raw = write_json(SOURCE_DIR / assessment.fari_id / asset.fari_id / stored_name, payload)
    document = AssetSource(
        assessment=assessment,
        asset=asset,
        fari_id=fari_id,
        filename=filename,
        stored_name=stored_name,
        file_format="cyclonedx",
        component_count=len(payload.get("components", [])),
        sha256=sha256_bytes(raw),
        byte_size=len(raw),
        mime_type="application/json",
        notes=notes,
        uploaded_at=clock.tick(),
    )
    db.session.add(document)
    db.session.flush()
    assessment.updated_at = clock.tick()
    return document


def add_inventory_component(clock: Clock, assessment: Assessment, asset: Asset, document: AssetSource, *, name: str, version: str, status: str) -> InventoryComponent:
    component = InventoryComponent(
        assessment=assessment,
        asset=asset,
        latest_document=document,
        fari_id=f"CMP-{assessment.id:04d}-{next_sequence(assessment.inventory_components, 'CMP'):03d}",
        name=name,
        ecosystem="generic",
        current_version=version,
        purl=f"pkg:generic/{name}@{version}",
        component_type="library",
        license_name="Unknown",
        status=status,
        notes="Seeded component timeline.",
        first_seen_at=document.uploaded_at,
        last_seen_at=document.uploaded_at,
    )
    db.session.add(component)
    db.session.flush()
    return component


def add_inventory_event(clock: Clock, component: InventoryComponent, document: AssetSource, *, event_type: str, summary: str, status_after: str, from_version: str = "", to_version: str = "", vulnerability_id: str = "", severity: str = "") -> InventoryEvent:
    event = InventoryEvent(
        component=component,
        document=document,
        fari_id=f"SBE-{component.id:04d}-{next_sequence(component.events, 'SBE'):03d}",
        event_type=event_type,
        occurred_at=clock.tick(),
        from_version=from_version,
        to_version=to_version,
        vulnerability_id=vulnerability_id,
        severity=severity,
        summary=summary,
        status_after=status_after,
        created_at=clock.tick(),
    )
    component.status = status_after
    if to_version:
        component.current_version = to_version
    component.last_seen_at = event.occurred_at
    db.session.add(event)
    db.session.flush()
    return event


def capture_version(clock: Clock, assessment: Assessment, *, summary: str, trigger: str = "manual_snapshot") -> None:
    assessment.updated_at = clock.tick()
    version = capture_assessment_version(assessment, trigger=trigger, summary=summary)
    version.created_at = clock.tick()
    db.session.add(version)
    db.session.flush()


def seed_standard_case(clock: Clock, *, title: str, client: str, segment: str, asset_name: str, investigation_title: str, claim: str, result: str, scenario: str, action: str, notes: str, finding: dict | None = None, status: str = "closed", gating: bool = True, context: str = "Seeded FARI validation case.") -> SeedCase:
    assessment = create_assessment(
        clock,
        title=title,
        client=client,
        context=context,
        scope=f"{asset_name} within the declared {segment} validation boundary.",
        authorization="Authorized internal validation for the seeded demonstration.",
        exclusions="Production deployment and behavior outside the declared boundary were not assessed.",
        status=status,
        maturity="final" if status == "closed" else "provisional",
    )
    asset = add_asset(clock, assessment, name=asset_name, segment=segment, description=f"Representative {segment} asset for the seeded case.")
    investigation = add_investigation(
        clock,
        assessment,
        asset,
        title=investigation_title,
        claim=claim,
        gating=gating,
        result=result,
        scenario=scenario,
        action=action,
        status="closed" if status == "closed" else "draft",
    )
    evidence = add_evidence(clock, investigation, filename="seeded-validation.txt", description="Seeded source material for the demonstration case.", body=f"case: {title}\nresult: {result}\nscenario: {scenario}")
    if finding:
        add_finding(clock, investigation, **finding)
    if status == "closed":
        capture_version(clock, assessment, summary=f"Seeded final state for {title}.", trigger="assessment_closed")
    else:
        capture_version(clock, assessment, summary=f"Initial intake snapshot for {title}.")
    return SeedCase(assessment, investigation, result, scenario, [("v1", f"Seeded state supported by {evidence.fari_id}.")], notes)


def seed_asset_source_case(clock: Clock) -> SeedCase:
    case = seed_standard_case(
        clock,
        title="Asset Source Vulnerability Lifecycle",
        client="Vector Orbit Labs",
        segment="supply_chain",
        asset_name="Mission Image Build",
        investigation_title="Dependency lifecycle verification",
        claim="Mission image builds exclude components with known vulnerable versions.",
        result="meets",
        scenario="not_demonstrated",
        action="accept",
        notes="Continuous-assurance example using asset sources, inventory events, and mitigation traceability.",
        context="Software supply-chain review before final release freeze.",
    )
    assessment = case.assessment
    asset = assessment.assets[0]
    document = add_asset_source(
        clock,
        assessment,
        asset,
        filename="mission-image.cdx.json",
        payload={"bomFormat": "CycloneDX", "specVersion": "1.5", "components": [{"name": "libfoo", "version": "1.4.5"}, {"name": "orbital-utils", "version": "5.2.1"}]},
        notes="Refreshed asset source after remediation.",
    )
    component = add_inventory_component(clock, assessment, asset, document, name="libfoo", version="1.4.5", status="fixed")
    add_inventory_event(clock, component, document, event_type="imported", summary="Refreshed asset source imported.", status_after="fixed", to_version="1.4.5")
    capture_version(clock, assessment, summary="Source refresh confirms the fixed dependency version.")
    case.versions.append(("v2", "Source refresh confirms libfoo 1.4.5 and closes the claim."))
    return case


def seed_orbit_reset_case(clock: Clock) -> SeedCase:
    """Seed the operational LEO reset/replay case and its four evidence files."""

    assessment = create_assessment(
        clock,
        title="Operational LEO Reset Command Replay",
        client="Asterion Orbital Operations",
        context=(
            "Operational low-Earth-orbit contact window with a flight-computer "
            "command receiver and supporting ground stations."
        ),
        scope=(
            "2026-05-14 operational contact event, the supplied RF capture, "
            "satellite execution logs, ground-station reconciliation, and a "
            "same-firmware engineering-model reproduction."
        ),
        authorization="Authorized retrospective investigation of an operational command event.",
        exclusions=(
            "Complete backup-station records, physical transmitter attribution, "
            "and a flight-vehicle laboratory reproduction were not supplied."
        ),
    )
    satellite = add_asset(
        clock,
        assessment,
        name="Operational LEO satellite flight computer",
        segment="space",
        description="Operational spacecraft flight computer and its CCSDS command receiver.",
        coverage="reviewed",
    )
    add_asset(
        clock,
        assessment,
        name="LEO contact ground-station network",
        segment="ground",
        description="Primary and backup ground stations participating in the scheduled contact window.",
        coverage="reviewed",
    )
    investigation = add_investigation(
        clock,
        assessment,
        satellite,
        title="Unauthenticated flight-computer reset command execution",
        claim=(
            "The operational command path rejects unauthenticated or replayed "
            "reset commands and preserves sufficient attribution to distinguish "
            "authorized commanding from an injected transmission."
        ),
        gating=True,
        result="does_not_meet",
        scenario="demonstrated",
        action="remediate",
        priority="immediate",
        method=(
            "Operational RF capture and satellite-log correlation, operations-plan "
            "reconciliation, and controlled same-firmware replay on an engineering model."
        ),
        facts=(
            "The event occurred on 2026-05-14 at 10:01:30 UTC during a scheduled "
            "contact window with an operational LEO satellite.\n"
            "A ground station captured a structurally valid CCSDS frame whose APID "
            "corresponds to the flight-computer reset command.\n"
            "The frame contains no cryptographic authentication mechanism, "
            "authentication tag, anti-replay counter, or freshness token.\n"
            "Satellite logs show that the command was received, accepted, and executed.\n"
            "The reset counter increased from 0186 to 0187 and telemetry was "
            "interrupted for approximately eight minutes.\n"
            "A same-firmware engineering-model test reproduced the reset on 5 of 5 attempts."
        ),
        inferences=(
            "The operational command path accepted and executed a reset command "
            "without an evidenced cryptographic authenticity or freshness check.\n"
            "The operational effect is consistent with the same command structure "
            "that caused repeatable resets in the engineering-model laboratory test."
        ),
        gaps=(
            "Logs from backup ground stations Bravo and Charlie were not provided.\n"
            "A single RF capture cannot determine the physical origin or identity "
            "of the transmitter.\n"
            "The engineering-model reproduction does not establish behavior on the "
            "flight vehicle under equivalent RF conditions."
        ),
        rationale=(
            "The operational execution and eight-minute telemetry interruption "
            "demonstrate that the claim fails within the declared event scope. "
            "Missing backup-station records and transmitter attribution constrain "
            "the source determination, while the laboratory result supports "
            "repeatability without replacing flight-vehicle validation."
        ),
        status="closed",
    )
    investigation.technical_reporter = "FARI incident investigation team"
    investigation.environment = (
        "Operational LEO contact window plus same-firmware laboratory replay on "
        "an engineering model."
    )
    investigation.assertions = (
        "The command dictionary identifies APID 0x042 as the flight-computer reset command."
    )
    investigation.contradictions = (
        "The satellite execution log records an accepted command, but the command "
        "is absent from the approved operations plan and primary station transmission log."
    )
    investigation.technical_sufficiency = "sufficient"
    investigation.reachability_sufficiency = "partial"
    investigation.mission_sufficiency = "partial"
    investigation.confidence = "medium"
    investigation.scope_boundary = (
        "The 2026-05-14 operational LEO contact event, supplied RF and satellite "
        "logs, station reconciliation, and same-firmware engineering-model replay; "
        "backup-station completeness, physical transmitter attribution, and flight-"
        "vehicle laboratory reproduction remain outside the evidenced boundary."
    )
    investigation.recommendations = (
        "Implement and verify cryptographic command authentication and anti-replay controls.\n"
        "Preserve synchronized logs from every primary and backup ground station for each contact window.\n"
        "Retest the reset command path on flight-representative hardware and the operational RF chain."
    )
    investigation.acceptance_criteria = (
        "An unauthenticated or replayed reset frame is rejected and logged as an integrity event.\n"
        "The same command cannot execute without an attributable authorized transmission record.\n"
        "A retest demonstrates telemetry recovery behavior within the approved mission limit."
    )
    db.session.add(investigation)
    db.session.flush()

    evidence_specs = [
        (
            "01-contact-window-rf-capture.txt",
            "Operational RF capture metadata and decoded CCSDS reset command.",
        ),
        (
            "02-satellite-execution-log.txt",
            "Satellite receipt, acceptance, execution, reset counter, and telemetry interruption log.",
        ),
        (
            "03-operations-reconciliation-and-gaps.txt",
            "Approved-plan and station-log reconciliation with explicit evidence gaps.",
        ),
        (
            "04-lab-repeatability-report.txt",
            "Same-firmware engineering-model repeatability report.",
        ),
    ]
    evidence = []
    for filename, description in evidence_specs:
        evidence.append(
            add_evidence(
                clock,
                investigation,
                filename=filename,
                description=description,
                body=(ORBIT_RESET_EVIDENCE_DIR / filename).read_text(encoding="utf-8"),
            )
        )

    capture_version(
        clock,
        assessment,
        summary=(
            "Operational event, RF capture, satellite execution log, and station "
            "reconciliation received for review."
        ),
    )
    add_finding(
        clock,
        investigation,
        title="Unauthenticated reset command was accepted and executed",
        state="confirmed",
        condition=(
            "The operational command receiver accepted and executed a valid CCSDS "
            "reset command without an evidenced authentication or replay check."
        ),
        effect="The flight-computer reset counter increased and telemetry was interrupted for eight minutes.",
        impact="An injected or replayed command can disrupt commandability and telemetry availability during operations.",
        mapping_state="candidate",
        mapping_rationale="No external framework mapping is required to establish the FARI claim failure.",
    )
    capture_version(
        clock,
        assessment,
        summary=(
            "Final investigation state records operational execution, explicit "
            "attribution gaps, and repeatable engineering-model impact."
        ),
        trigger="assessment_closed",
    )
    return SeedCase(
        assessment,
        investigation,
        "does_not_meet",
        "demonstrated",
        [
            ("v1", f"Initial event and evidence intake supported by {evidence[0].fari_id}–{evidence[-1].fari_id}."),
            ("v2", "Final state records execution, telemetry impact, and unresolved transmitter attribution."),
        ],
        "Operational LEO example combining strong effect evidence with explicit ground-station and attribution gaps.",
    )


def seed_cases(clock: Clock) -> list[SeedCase]:
    return [
        seed_standard_case(clock, title="Command Auth Fallback Review", client="Helios Dynamics", segment="ground", asset_name="Command Bridge", investigation_title="Legacy bridge authentication review", claim="The command bridge rejects unauthorized command paths.", result="does_not_meet", scenario="demonstrated", action="remediate", notes="Partial mitigation case that remains Does Not Meet.", finding={"title": "Legacy bridge accepts an unauthorized command path", "state": "confirmed", "condition": "The maintenance bridge accepts a command path without the expected authorization check.", "effect": "An unauthorized test command reached the bridge parser.", "impact": "The command path can be influenced within the tested maintenance boundary.", "mapping_state": "confirmed", "mapping_rationale": "The finding is directly tied to the claim and supplied evidence."}),
        seed_standard_case(clock, title="Privileged Operator MFA Rollout", client="Helios Dynamics", segment="ground", asset_name="Operator Portal", investigation_title="Privileged access validation", claim="Privileged operator access requires the declared authentication controls.", result="meets", scenario="not_demonstrated", action="accept", notes="Clean mitigation success with a clear audit trail."),
        seed_standard_case(clock, title="Replay Window Characterization", client="Vector Orbit Labs", segment="link", asset_name="Command Receiver", investigation_title="Freshness-window characterization", claim="The command receiver rejects replayed frames across the accepted freshness window.", result="inconclusive", scenario="plausible", action="extend_investigation", notes="Inconclusive case pending longer-window validation.", finding={"title": "Replay resistance is not fully characterized", "state": "candidate", "condition": "Short-window replays were rejected, but extended-delay coverage remains absent.", "effect": "The receiver behavior is only partially evidenced.", "impact": "Replay resilience could still break at untested delay conditions.", "mapping_state": "candidate", "mapping_rationale": "The mapping records the relationship between the finding and the freshness claim."}),
        seed_standard_case(clock, title="Telemetry API RBAC Review", client="Northstar Telemetry", segment="cloud", asset_name="Telemetry Control API", investigation_title="Role authorization and audit review", claim="Telemetry API roles enforce the intended authorization boundary and record relevant actions.", result="meets", scenario="not_demonstrated", action="accept", notes="Cloud reference for a clean success case."),
        seed_standard_case(clock, title="Third-Party Firmware Intake", client="Asterion Systems", segment="supply_chain", asset_name="Supplier Firmware Package", investigation_title="Supplier package intake", claim="The supplier package has sufficient evidence for a final acceptance decision.", result="not_assessed", scenario="not_evaluated", action="extend_investigation", notes="Non-gating draft intake case used to exercise Not Assessed.", status="draft", gating=False),
        seed_asset_source_case(clock),
        seed_standard_case(clock, title="Command-Link Confidentiality Rehearsal", client="Asterion Systems", segment="link", asset_name="Command Link", investigation_title="Confidentiality control rehearsal", claim="The declared command-link rehearsal preserves confidentiality within its stated boundary.", result="meets", scenario="plausible", action="accept", notes="Scoped Meets result based on compensating operational controls."),
        seed_orbit_reset_case(clock),
    ]


def render_catalog(cases: list[SeedCase]) -> None:
    lines = [
        "# FARI Scenario Test Catalog",
        "",
        "Seeded workspace catalog for the local FARI demo database.",
        "",
        "The workspace is reset and repopulated to cover the main FARI claim outcomes,",
        "scenario dispositions, mitigation traces, asset-source lifecycle behavior, and an operational LEO command-replay case.",
        "",
        "## Coverage summary",
        "",
        "- `Does Not Meet`: present in current state and in initial mitigation snapshots.",
        "- `Meets`: present in clean success, mitigation-success, and compensating-control cases.",
        "- `Inconclusive`: present as a closed replay-characterization case.",
        "- `Not Assessed`: present as a draft non-gating intake case.",
        "- Operational command replay: present as a demonstrated Does Not Meet case with explicit attribution gaps.",
        "- `Demonstrated`, `Plausible`, `Not Demonstrated`, and `Not Evaluated` are all represented.",
        "",
        "## Assessments",
        "",
        "| Assessment | Current result | Scenario disposition | Versions | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in cases:
        versions = "<br>".join(f"{label}: {summary}" for label, summary in item.versions)
        lines.append(f"| `{item.assessment.fari_id}` {item.assessment.title} | `{item.current_result}` | `{item.current_scenario}` | {versions} | {item.notes} |")
    lines.extend([
        "",
        "## Filter expectations",
        "",
        "- Portfolio filters should show closed assessments in `meets`, `does_not_meet`, and `inconclusive`.",
        "- The draft intake case should keep a genuine `not_assessed` overall state because its investigation is non-gating.",
        "- Traceability comparisons should be most interesting on the MFA rollout, auth fallback, and asset-source lifecycle cases.",
        "",
        "## Suggested demo order",
        "",
        "1. `ASM-2026-0001` for a partial mitigation that still fails.",
        "2. `ASM-2026-0002` for a clean mitigation success.",
        "3. `ASM-2026-0003` for a defensible inconclusive result.",
        "4. `ASM-2026-0005` for a true draft intake.",
        "5. `ASM-2026-0006` for asset-source-driven continuous assurance.",
        "6. The operational LEO reset replay case for a demonstrated effect with incomplete source attribution.",
    ])
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    reset_workspace()
    app = make_app()
    with app.app_context():
        db.session.remove()
        reset_database_schema()
        cases = seed_cases(Clock(BASE_TIME))
        db.session.commit()
        render_catalog(cases)
        print(f"Seeded {len(cases)} assessments into {db.engine.url.render_as_string(hide_password=False)}")
        for item in cases:
            result = overall_conclusion(item.assessment.investigations)
            print(f"- {item.assessment.fari_id} | assessment={result} | claim={item.current_result} | scenario={item.current_scenario}")
        print(f"Catalog written to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
