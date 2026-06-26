"""Reset the local FARI workspace data and seed realistic scenario cases."""

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

from webapp.compliance import (
    SPD5_SCENARIOS,
    seed_spd5_companion,
    sync_profile_posture,
)
from webapp.db import (
    Assessment,
    Asset,
    ComplianceProfile,
    Evidence,
    Finding,
    Investigation,
    InventoryComponent,
    InventoryEvent,
    SbomDocument,
    db,
    init_app as init_db,
    next_sequence,
)
from webapp.reporting import overall_conclusion
from webapp.traceability import capture_assessment_version


INSTANCE_DIR = Path(os.environ.get("FARI_DATA_DIR", PROJECT_ROOT / "instance"))
EVIDENCE_DIR = INSTANCE_DIR / "evidence"
ATTACK_FLOW_DIR = INSTANCE_DIR / "attack_flows"
SBOM_DIR = INSTANCE_DIR / "sbom"
DATABASE_PATH = INSTANCE_DIR / "fari.sqlite3"
CATALOG_PATH = PROJECT_ROOT / "spec" / "current" / "reports" / "FARI-SCENARIO-TEST-CATALOG.md"
BASE_TIME = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


@dataclass
class SeedCase:
    assessment: Assessment
    investigation: Investigation | None
    profile: ComplianceProfile | None
    current_result: str
    current_scenario: str
    companion_scenario: str
    posture: str
    versions: list[tuple[str, str]]
    notes: str


class Clock:
    def __init__(self, start: datetime):
        self.current = start

    def tick(self, minutes: int = 17) -> str:
        stamp = self.current
        self.current = self.current + timedelta(minutes=minutes)
        return stamp.replace(microsecond=0).isoformat()


def reset_workspace() -> None:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    for path in (EVIDENCE_DIR, ATTACK_FLOW_DIR, SBOM_DIR):
        if path.exists():
            shutil.rmtree(path)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ATTACK_FLOW_DIR.mkdir(parents=True, exist_ok=True)
    SBOM_DIR.mkdir(parents=True, exist_ok=True)
    if not configured_database_url() and DATABASE_PATH.exists():
        DATABASE_PATH.unlink()


def configured_database_url() -> str | None:
    url = os.environ.get("FARI_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        return None
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def make_app() -> Flask:
    app = Flask(__name__)
    database_url = configured_database_url()
    app.config["SECRET_KEY"] = "fari-seed"
    app.config["DATABASE"] = str(DATABASE_PATH)
    app.config["UPLOAD_DIR"] = str(EVIDENCE_DIR)
    app.config["ATTACK_FLOW_DIR"] = str(ATTACK_FLOW_DIR)
    app.config["SBOM_DIR"] = str(SBOM_DIR)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///" + str(DATABASE_PATH)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    init_db(app)
    return app


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def create_assessment(
    clock: Clock,
    *,
    client_name: str,
    title: str,
    mission_context: str,
    scope: str,
    authorization: str,
    exclusions: str,
    status: str = "draft",
    maturity: str = "provisional",
) -> Assessment:
    assessment = Assessment(
        client_name=client_name,
        title=title,
        mission_context=mission_context,
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


def add_asset(
    clock: Clock,
    assessment: Assessment,
    *,
    name: str,
    segment: str,
    description: str,
    access_model: str,
    coverage: str,
) -> Asset:
    sequence = next_sequence(assessment.assets, "AST")
    asset = Asset(
        assessment=assessment,
        fari_id=f"AST-{assessment.id:04d}-{sequence:03d}",
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


def add_investigation(
    clock: Clock,
    assessment: Assessment,
    asset: Asset | None,
    *,
    title: str,
    claim_description: str,
    gating: bool,
    technical_reporter: str,
    method: str,
    environment: str,
    facts: str,
    assertions: str,
    inferences: str,
    assumptions: str,
    contradictions: str,
    gaps: str,
    technical_sufficiency: str,
    reachability_sufficiency: str,
    mission_sufficiency: str,
    conclusion: str,
    scenario_state: str,
    confidence: str,
    required_action: str,
    priority: str,
    scope_boundary: str,
    rationale: str,
    recommendations: str,
    acceptance_criteria: str,
    status: str,
) -> Investigation:
    sequence = next_sequence(assessment.investigations, "INV")
    investigation = Investigation(
        assessment=assessment,
        asset=asset,
        fari_id=f"INV-{assessment.id:04d}-{sequence:03d}",
        claim_id=f"CLM-{assessment.id:04d}-{sequence:03d}",
        title=title,
        claim_description=claim_description,
        gating=gating,
        technical_reporter=technical_reporter,
        method=method,
        environment=environment,
        facts=facts,
        assertions=assertions,
        inferences=inferences,
        assumptions=assumptions,
        contradictions=contradictions,
        gaps=gaps,
        technical_sufficiency=technical_sufficiency,
        reachability_sufficiency=reachability_sufficiency,
        mission_sufficiency=mission_sufficiency,
        conclusion=conclusion,
        scenario_state=scenario_state,
        confidence=confidence,
        required_action=required_action,
        priority=priority,
        scope_boundary=scope_boundary,
        rationale=rationale,
        recommendations=recommendations,
        acceptance_criteria=acceptance_criteria,
        status=status,
        created_at=clock.tick(),
        updated_at=clock.tick(),
    )
    db.session.add(investigation)
    db.session.flush()
    assessment.updated_at = clock.tick()
    return investigation


def add_evidence(
    clock: Clock,
    investigation: Investigation,
    *,
    filename: str,
    description: str,
    body: str,
    mime_type: str = "text/plain",
) -> Evidence:
    sequence = next_sequence(investigation.evidence, "EVD")
    fari_id = f"EVD-{investigation.id:04d}-{sequence:03d}"
    stored_name = f"{fari_id}-{filename}"
    target = EVIDENCE_DIR / investigation.fari_id / stored_name
    raw = body.strip().encode("utf-8") + b"\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    item = Evidence(
        investigation=investigation,
        fari_id=fari_id,
        filename=filename,
        stored_name=stored_name,
        description=description,
        sha256=sha256_bytes(raw),
        mime_type=mime_type,
        uploaded_at=clock.tick(),
    )
    db.session.add(item)
    db.session.flush()
    investigation.updated_at = clock.tick()
    investigation.assessment.updated_at = clock.tick()
    return item


def add_finding(
    clock: Clock,
    investigation: Investigation,
    *,
    title: str,
    state: str,
    condition_text: str,
    observed_effect: str,
    credible_impact: str,
    sparta_id: str = "",
    sparta_name: str = "",
    mapping_state: str = "candidate",
    mapping_rationale: str = "",
    include_sparta_countermeasures: bool = False,
) -> Finding:
    sequence = next_sequence(investigation.findings, "FND")
    finding = Finding(
        investigation=investigation,
        fari_id=f"FND-{investigation.id:04d}-{sequence:03d}",
        title=title,
        state=state,
        condition_text=condition_text,
        observed_effect=observed_effect,
        credible_impact=credible_impact,
        sparta_id=sparta_id,
        sparta_name=sparta_name,
        mapping_state=mapping_state,
        mapping_rationale=mapping_rationale,
        include_sparta_countermeasures=include_sparta_countermeasures,
        created_at=clock.tick(),
    )
    db.session.add(finding)
    db.session.flush()
    investigation.updated_at = clock.tick()
    investigation.assessment.updated_at = clock.tick()
    return finding


def add_sbom_document(
    clock: Clock,
    assessment: Assessment,
    asset: Asset | None,
    *,
    filename: str,
    payload: dict,
    file_format: str,
    notes: str,
) -> SbomDocument:
    sequence = next_sequence(assessment.sbom_documents, "SBM")
    fari_id = f"SBM-{assessment.id:04d}-{sequence:03d}"
    stored_name = f"{fari_id}-{filename}"
    target = SBOM_DIR / assessment.fari_id / stored_name
    raw = json.dumps(payload, indent=2).encode("utf-8") + b"\n"
    write_json(target, payload)
    document = SbomDocument(
        assessment=assessment,
        asset=asset,
        fari_id=fari_id,
        filename=filename,
        stored_name=stored_name,
        file_format=file_format,
        component_count=len(payload.get("components", [])),
        sha256=sha256_bytes(raw),
        notes=notes,
        uploaded_at=clock.tick(),
    )
    db.session.add(document)
    db.session.flush()
    assessment.updated_at = clock.tick()
    return document


def add_inventory_component(
    clock: Clock,
    assessment: Assessment,
    asset: Asset | None,
    document: SbomDocument,
    *,
    name: str,
    ecosystem: str,
    version: str,
    status: str,
    purl: str,
    component_type: str,
    license_name: str,
    notes: str,
) -> InventoryComponent:
    sequence = next_sequence(assessment.inventory_components, "CMP")
    component = InventoryComponent(
        assessment=assessment,
        asset=asset,
        latest_document=document,
        fari_id=f"CMP-{assessment.id:04d}-{sequence:03d}",
        name=name,
        ecosystem=ecosystem,
        current_version=version,
        purl=purl,
        component_type=component_type,
        license_name=license_name,
        status=status,
        notes=notes,
        first_seen_at=document.uploaded_at,
        last_seen_at=document.uploaded_at,
    )
    db.session.add(component)
    db.session.flush()
    return component


def add_inventory_event(
    clock: Clock,
    component: InventoryComponent,
    document: SbomDocument | None,
    *,
    event_type: str,
    summary: str,
    status_after: str,
    from_version: str = "",
    to_version: str = "",
    vulnerability_id: str = "",
    severity: str = "",
) -> InventoryEvent:
    sequence = next_sequence(component.events, "SBE")
    event = InventoryEvent(
        component=component,
        document=document,
        fari_id=f"SBE-{component.id:04d}-{sequence:03d}",
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
    component.assessment.updated_at = clock.tick()
    return event


def capture_version(
    clock: Clock,
    assessment: Assessment,
    *,
    summary: str,
    trigger: str = "manual_snapshot",
) -> None:
    assessment.updated_at = clock.tick()
    version = capture_assessment_version(assessment, trigger=trigger, summary=summary)
    version.created_at = clock.tick()
    db.session.add(version)
    db.session.flush()


def apply_companion(
    profile: ComplianceProfile,
    *,
    scenario: str,
    summary: str,
    notes: str,
    statuses: dict[str, str],
    refs: dict[str, str] | None = None,
    control_notes: dict[str, str] | None = None,
) -> None:
    refs = refs or {}
    control_notes = control_notes or {}
    profile.scenario = scenario
    profile.summary = summary
    profile.notes = notes
    for check in profile.checks:
        check.status = statuses.get(check.control_id, "not_applicable")
        check.evidence_refs = refs.get(check.control_id, "")
        check.notes = control_notes.get(check.control_id, "")
    sync_profile_posture(profile)


def seed_case_01(clock: Clock) -> SeedCase:
    assessment = create_assessment(
        clock,
        client_name="Helios Dynamics",
        title="Command Auth Fallback Review",
        mission_context="FlatSat validation of telecommand acceptance before integrated mission rehearsal.",
        scope="RF command decoder, command router, and engineering bridge compatibility path.",
        authorization="Internal security validation on representative bench hardware.",
        exclusions="No live RF emission outside the shielded lab and no on-orbit control path.",
        status="draft",
        maturity="provisional",
    )
    asset = add_asset(
        clock,
        assessment,
        name="Command Router",
        segment="space",
        description="Bench OBC command parser and bridge adapter.",
        access_model="white_box",
        coverage="tested",
    )
    investigation = add_investigation(
        clock,
        assessment,
        asset,
        title="Unsigned telecommand acceptance",
        claim_description="Unsigned telecommands are rejected before command dispatch.",
        gating=True,
        technical_reporter="Lab Integration Team",
        method="Scripted telecommand injection over RF decode output and engineering bridge replay.",
        environment="Shielded FlatSat bench with debug bridge enabled.",
        facts="Unsigned command frames reached the dispatch queue.\nThe command counter incremented.\nNo MAC validation failure was recorded in the bridge path.",
        assertions="The replayed frame body matches the nominal command format used by the router.",
        inferences="The compatibility bridge bypasses the same authentication check used on the RF path.",
        assumptions="The engineering bridge remains enabled during integration windows.",
        contradictions="The vendor note states legacy mode is disabled by default, but the bench image kept it enabled.",
        gaps="No proof that the same debug bridge remains reachable in flight operations.",
        technical_sufficiency="sufficient",
        reachability_sufficiency="partial",
        mission_sufficiency="partial",
        conclusion="does_not_meet",
        scenario_state="demonstrated",
        confidence="high",
        required_action="remediate",
        priority="immediate",
        scope_boundary="Conclusion applies to the tested RF decoder output and engineering bridge path on the FlatSat image.",
        rationale="The tested parser accepted an unsigned command on a reachable integration path.",
        recommendations="Disable the legacy bridge by default.\nBind bridge acceptance to the same MAC enforcement used on the RF path.",
        acceptance_criteria="Unsigned command replay is rejected on every enabled ingress path.",
        status="ready",
    )
    ev1 = add_evidence(
        clock,
        investigation,
        filename="bridge_acceptance_log.txt",
        description="Initial bridge replay showing unsigned command acceptance.",
        body="""
        test_case: unsigned_cmd_bridge_replay
        result: accepted
        queue_depth: 1
        log_note: no mac validation event emitted
        """,
    )
    add_finding(
        clock,
        investigation,
        title="Legacy command bridge accepts unsigned commands",
        state="confirmed",
        condition_text="The legacy bridge forwards a syntactically valid command without MAC enforcement.",
        observed_effect="Command dispatch increments after replay through the bridge.",
        credible_impact="A retained engineering path could bypass telecommand authentication during integration.",
        sparta_id="EX-0014.02",
        sparta_name="Bus Traffic Spoofing",
        mapping_state="confirmed",
        mapping_rationale="A spoofed command body bypassed the expected trust boundary on an internal control path.",
    )
    profile = seed_spd5_companion(assessment)
    db.session.add(profile)
    apply_companion(
        profile,
        scenario="partial_alignment",
        summary="Primary command authentication exists, but a legacy compatibility path still weakens enforcement.",
        notes="This profile intentionally stays narrow and follows the declared integration scope.",
        statuses={
            "SPD5-GOV-01": "implemented",
            "SPD5-GOV-02": "implemented",
            "SPD5-GOV-03": "implemented",
            "SPD5-GOV-04": "planned",
            "SPD5-SPC-01": "not_implemented",
            "SPD5-SPC-05": "partially_implemented",
            "SPD5-COM-02": "partially_implemented",
            "SPD5-GRD-03": "implemented",
            "SPD5-MON-03": "implemented",
        },
        refs={
            "SPD5-GOV-02": investigation.fari_id,
            "SPD5-SPC-01": f"{investigation.fari_id}, {ev1.fari_id}",
            "SPD5-COM-02": investigation.fari_id,
        },
        control_notes={
            "SPD5-SPC-01": "The RF parser rejects unsigned commands, but the enabled bridge does not.",
            "SPD5-SPC-05": "Recovery procedure exists, though it assumes the bridge can be disabled manually.",
        },
    )
    capture_version(
        clock,
        assessment,
        summary="Initial confirmed auth bypass on the legacy command bridge.",
    )

    add_evidence(
        clock,
        investigation,
        filename="post_patch_bridge_log.txt",
        description="Post-patch validation showing the RF path fixed but the maintenance bridge still enabled.",
        body="""
        test_case: post_patch_unsigned_cmd_validation
        rf_path: rejected
        maintenance_bridge: accepted
        operator_note: bridge remains enabled for integration burn-in
        """,
    )
    investigation.facts = (
        "Unsigned frames are rejected on the RF path after the patch.\n"
        "The maintenance bridge still accepts an unsigned command body.\n"
        "The command router dispatch counter increments when replay uses the maintenance bridge."
    )
    investigation.inferences = (
        "The remediation closed the intended path but left the maintenance ingress as a residual bypass."
    )
    investigation.gaps = "No evidence shows whether the maintenance bridge is reachable outside bench integration."
    investigation.conclusion = "does_not_meet"
    investigation.scenario_state = "demonstrated"
    investigation.required_action = "retest"
    investigation.priority = "immediate"
    investigation.rationale = (
        "The patched system still accepts an unsigned command through an enabled maintenance ingress."
    )
    investigation.acceptance_criteria = (
        "Every enabled command ingress rejects unsigned traffic and logs the rejection."
    )
    investigation.status = "closed"
    investigation.updated_at = clock.tick()
    assessment.status = "closed"
    assessment.maturity = "final"
    profile.summary = (
        "Partial remediation landed on the RF path, but the command-authentication claim still fails overall."
    )
    apply_companion(
        profile,
        scenario="partial_alignment",
        summary=profile.summary,
        notes="Good example of a mitigation that improves posture without fully resolving the claim.",
        statuses={
            "SPD5-GOV-01": "implemented",
            "SPD5-GOV-02": "implemented",
            "SPD5-GOV-03": "implemented",
            "SPD5-GOV-04": "implemented",
            "SPD5-SPC-01": "partially_implemented",
            "SPD5-SPC-05": "partially_implemented",
            "SPD5-COM-02": "partially_implemented",
            "SPD5-GRD-03": "implemented",
            "SPD5-MON-03": "implemented",
        },
        refs={
            "SPD5-SPC-01": investigation.fari_id,
            "SPD5-COM-02": investigation.fari_id,
        },
        control_notes={
            "SPD5-SPC-01": "The residual bridge path prevents a full implementation statement.",
        },
    )
    capture_version(
        clock,
        assessment,
        summary="Partial mitigation applied; residual bridge bypass keeps the claim open.",
        trigger="assessment_closed",
    )
    return SeedCase(
        assessment=assessment,
        investigation=investigation,
        profile=profile,
        current_result=investigation.conclusion,
        current_scenario=investigation.scenario_state,
        companion_scenario=profile.scenario,
        posture=profile.posture,
        versions=[
            ("v1", "Initial confirmed bypass on the legacy bridge."),
            ("v2", "RF path fixed, residual maintenance bridge keeps the finding open."),
        ],
        notes="Covers a realistic partial mitigation where the executive result remains Does Not Meet.",
    )


def seed_case_02(clock: Clock) -> SeedCase:
    assessment = create_assessment(
        clock,
        client_name="Aurora Mission Control",
        title="Privileged Operator MFA Rollout",
        mission_context="Ground-segment access control review before joint mission operations.",
        scope="Operator portal, identity provider, and privileged session approval flow.",
        authorization="Authorized configuration review and controlled login testing.",
        exclusions="No phishing simulation and no third-party SSO outage testing.",
        status="draft",
        maturity="provisional",
    )
    asset = add_asset(
        clock,
        assessment,
        name="Operator Access Portal",
        segment="ground",
        description="Privileged mission portal used for command preparation and approvals.",
        access_model="grey_box",
        coverage="tested",
    )
    investigation = add_investigation(
        clock,
        assessment,
        asset,
        title="Privileged login without MFA",
        claim_description="Privileged operator sessions require MFA before access is granted.",
        gating=True,
        technical_reporter="External Controls Reviewer",
        method="Configuration review, privileged login attempt, and audit verification.",
        environment="Staging ground segment with production-equivalent IAM policies.",
        facts="A privileged operator account authenticated with username and password only.\nThe portal granted access to the approval dashboard.\nNo MFA challenge appeared in the login audit trail.",
        assertions="The tested account carried the same role bundle used by shift leads.",
        inferences="The privileged path depended on password-only authentication at the time of review.",
        assumptions="The observed login policy would also affect real operator accounts if promoted unchanged.",
        contradictions="Portal documentation claimed MFA was mandatory, but the staging policy had an exception.",
        gaps="No evidence yet that the exception had been removed everywhere.",
        technical_sufficiency="sufficient",
        reachability_sufficiency="sufficient",
        mission_sufficiency="partial",
        conclusion="does_not_meet",
        scenario_state="plausible",
        confidence="high",
        required_action="remediate",
        priority="immediate",
        scope_boundary="Conclusion applies to the tested privileged login flow in the staged ground environment.",
        rationale="The privileged path granted access without the required second factor.",
        recommendations="Remove the staging exception.\nRequire MFA enrollment before operator-role assignment.",
        acceptance_criteria="Every privileged session logs a successful MFA challenge before portal access.",
        status="ready",
    )
    ev1 = add_evidence(
        clock,
        investigation,
        filename="staging_login_audit.txt",
        description="Audit excerpt showing password-only privileged login.",
        body="""
        actor: shiftlead-test
        role_bundle: mission-approver
        mfa_challenge: absent
        portal_access: granted
        """,
    )
    add_finding(
        clock,
        investigation,
        title="Privileged ground login bypasses MFA requirement",
        state="confirmed",
        condition_text="A role exception permits password-only access to the privileged portal.",
        observed_effect="The approval dashboard becomes available without second-factor verification.",
        credible_impact="Compromised operator credentials could immediately access privileged functions.",
        mapping_state="confirmed",
        mapping_rationale="The tested role path clearly skipped the expected control.",
    )
    profile = seed_spd5_companion(assessment)
    db.session.add(profile)
    apply_companion(
        profile,
        scenario="partial_alignment",
        summary="Identity governance exists, but privileged MFA enforcement was incomplete during staging.",
        notes="Useful for validating the line between a policy statement and operational enforcement.",
        statuses={
            "SPD5-GOV-01": "implemented",
            "SPD5-GOV-02": "implemented",
            "SPD5-GOV-04": "implemented",
            "SPD5-GRD-01": "not_implemented",
            "SPD5-GRD-02": "implemented",
            "SPD5-GRD-03": "implemented",
            "SPD5-GRD-04": "implemented",
            "SPD5-GRD-05": "implemented",
            "SPD5-MON-03": "implemented",
        },
        refs={
            "SPD5-GRD-01": f"{investigation.fari_id}, {ev1.fari_id}",
            "SPD5-GRD-03": investigation.fari_id,
        },
    )
    capture_version(
        clock,
        assessment,
        summary="Initial privileged-access review found the MFA exception still active.",
    )

    add_evidence(
        clock,
        investigation,
        filename="mfa_enforced_login.txt",
        description="Retest showing the privileged flow now requires MFA.",
        body="""
        actor: shiftlead-test
        role_bundle: mission-approver
        mfa_challenge: passed
        portal_access: granted
        """,
    )
    investigation.facts = (
        "The staging exception was removed.\n"
        "A privileged login now requires MFA.\n"
        "The audit trail records the MFA challenge and success event."
    )
    investigation.inferences = "The privileged login path now enforces the declared access-control policy."
    investigation.gaps = "No residual MFA gaps were observed in the tested privileged role set."
    investigation.technical_sufficiency = "sufficient"
    investigation.reachability_sufficiency = "sufficient"
    investigation.mission_sufficiency = "sufficient"
    investigation.conclusion = "meets"
    investigation.scenario_state = "not_demonstrated"
    investigation.required_action = "accept"
    investigation.priority = "planned"
    investigation.rationale = "The retest confirmed the required MFA control on the privileged access path."
    investigation.recommendations = "Keep the exception list empty.\nRetest after any identity-provider policy change."
    investigation.acceptance_criteria = "Privileged access remains MFA-gated and exceptions require explicit approval."
    investigation.status = "closed"
    investigation.updated_at = clock.tick()
    assessment.status = "closed"
    assessment.maturity = "final"
    apply_companion(
        profile,
        scenario="evidence_backed_alignment",
        summary="The privileged ground-access path now aligns with the expected control set for the tested scope.",
        notes="Good mitigation case for showing a clean Does Not Meet to Meets transition.",
        statuses={
            "SPD5-GOV-01": "implemented",
            "SPD5-GOV-02": "implemented",
            "SPD5-GOV-04": "implemented",
            "SPD5-GRD-01": "implemented",
            "SPD5-GRD-02": "implemented",
            "SPD5-GRD-03": "implemented",
            "SPD5-GRD-04": "implemented",
            "SPD5-GRD-05": "implemented",
            "SPD5-MON-03": "implemented",
        },
        refs={
            "SPD5-GRD-01": investigation.fari_id,
            "SPD5-GRD-03": investigation.fari_id,
            "SPD5-MON-03": investigation.fari_id,
        },
    )
    capture_version(
        clock,
        assessment,
        summary="MFA rollout verified on the privileged portal path.",
        trigger="assessment_closed",
    )
    return SeedCase(
        assessment=assessment,
        investigation=investigation,
        profile=profile,
        current_result=investigation.conclusion,
        current_scenario=investigation.scenario_state,
        companion_scenario=profile.scenario,
        posture=profile.posture,
        versions=[
            ("v1", "Password-only privileged access confirmed."),
            ("v2", "MFA enforced and retested successfully."),
        ],
        notes="Canonical mitigation example that ends in Meets with a clear audit trail.",
    )


def seed_case_03(clock: Clock) -> SeedCase:
    assessment = create_assessment(
        clock,
        client_name="Vector Orbit Labs",
        title="Replay Window Characterization",
        mission_context="Link-layer resilience review before full RF interoperability testing.",
        scope="Bench replay testing against the command receiver freshness window.",
        authorization="Internal lab validation with recorded link traffic.",
        exclusions="No long-duration orbital delay simulation and no production key-rollover exercise.",
        status="closed",
        maturity="final",
    )
    asset = add_asset(
        clock,
        assessment,
        name="UHF Command Receiver",
        segment="link",
        description="Receiver and freshness validator used on the command uplink path.",
        access_model="grey_box",
        coverage="tested",
    )
    investigation = add_investigation(
        clock,
        assessment,
        asset,
        title="Freshness-window replay characterization",
        claim_description="The command receiver rejects replayed frames outside the accepted freshness window.",
        gating=True,
        technical_reporter="RF Validation Team",
        method="Recorded frame replay with bounded delay offsets.",
        environment="Shielded receiver bench with captured command frames and controlled replay intervals.",
        facts="Immediate replay attempts were rejected.\nDelayed replay beyond the short test window was not executed.\nKey rollover timing was not exercised.",
        assertions="The same replay harness can support longer delay offsets when an extended booking is available.",
        inferences="The current evidence is favorable but does not resolve the claim across the full operational window.",
        assumptions="Operational key rollover could change replay behavior at longer delays.",
        contradictions="None observed in the supplied material.",
        gaps="No long-delay replay data.\nNo key-rollover coverage.\nNo independent telemetry proof across the full freshness interval.",
        technical_sufficiency="partial",
        reachability_sufficiency="partial",
        mission_sufficiency="partial",
        conclusion="inconclusive",
        scenario_state="plausible",
        confidence="medium",
        required_action="extend_investigation",
        priority="planned",
        scope_boundary="Conclusion applies only to the tested short-delay replay window on the bench receiver.",
        rationale="The available replay data is encouraging but too narrow to support a complete acceptance statement.",
        recommendations="Repeat the replay at longer delay offsets.\nInclude key-rollover timing in the next retest.",
        acceptance_criteria="The receiver rejects replay across the full accepted timing window, including rollover conditions.",
        status="closed",
    )
    ev1 = add_evidence(
        clock,
        investigation,
        filename="short_window_replay_summary.txt",
        description="Short-window replay summary with no long-delay coverage.",
        body="""
        replay_offset_ms: 250
        receiver_decision: rejected
        long_window_test: not_run
        key_rollover_test: not_run
        """,
    )
    add_finding(
        clock,
        investigation,
        title="Replay resistance not fully characterized",
        state="candidate",
        condition_text="Short-window replays were rejected, but extended-delay coverage remains absent.",
        observed_effect="The receiver behavior is only partially evidenced.",
        credible_impact="Replay resilience could still break at untested delay or rollover conditions.",
        sparta_id="EX-0014.02",
        sparta_name="Replay-Like Command Reuse",
        mapping_state="candidate",
        mapping_rationale="The assessed path concerns freshness and replay handling on a control link.",
    )
    profile = seed_spd5_companion(assessment)
    db.session.add(profile)
    apply_companion(
        profile,
        scenario="inconclusive_scope_boundary",
        summary="The command-link baseline is promising, but the present evidence cannot close replay assurance end to end.",
        notes="This is the cleanest example of an inconclusive case that still says something useful.",
        statuses={
            "SPD5-GOV-02": "implemented",
            "SPD5-GOV-03": "implemented",
            "SPD5-COM-01": "not_verified",
            "SPD5-COM-02": "implemented",
            "SPD5-COM-03": "implemented",
            "SPD5-COM-05": "implemented",
            "SPD5-MON-02": "implemented",
            "SPD5-MON-01": "not_verified",
        },
        refs={
            "SPD5-COM-01": f"{investigation.fari_id}, {ev1.fari_id}",
            "SPD5-MON-02": investigation.fari_id,
        },
        control_notes={
            "SPD5-COM-01": "Not enough data exists for a full implementation statement.",
        },
    )
    capture_version(
        clock,
        assessment,
        summary="Replay characterization closed as inconclusive pending longer-window validation.",
        trigger="assessment_closed",
    )
    return SeedCase(
        assessment=assessment,
        investigation=investigation,
        profile=profile,
        current_result=investigation.conclusion,
        current_scenario=investigation.scenario_state,
        companion_scenario=profile.scenario,
        posture=profile.posture,
        versions=[("v1", "Short-window replay retest only; full freshness coverage still pending.")],
        notes="Reference case for Inconclusive plus Plausible and an inconclusive SPD-5 overlay.",
    )


def seed_case_04(clock: Clock) -> SeedCase:
    assessment = create_assessment(
        clock,
        client_name="Northstar Telemetry",
        title="Telemetry API RBAC Review",
        mission_context="Cloud control-plane review before customer read-only telemetry rollout.",
        scope="Hosted telemetry API authorization, role mapping, and command-path logging.",
        authorization="Internal application review with temporary analyst and admin tokens.",
        exclusions="No denial-of-service testing and no external identity-provider compromise simulation.",
        status="closed",
        maturity="final",
    )
    asset = add_asset(
        clock,
        assessment,
        name="Telemetry Control API",
        segment="cloud",
        description="Hosted API providing telemetry reads and limited state-changing actions.",
        access_model="grey_box",
        coverage="reviewed",
    )
    investigation = add_investigation(
        clock,
        assessment,
        asset,
        title="Analyst role command restriction",
        claim_description="Analyst-role users cannot issue spacecraft state-changing commands through the telemetry API.",
        gating=True,
        technical_reporter="Platform Security",
        method="Role review, scoped token test, and audit-log correlation.",
        environment="Staging cloud environment with production-equivalent role bindings.",
        facts="The analyst token could read telemetry.\nA state-changing API request returned HTTP 403.\nThe audit log recorded the denied command attempt.",
        assertions="The tested role mapping matches the customer analyst template.",
        inferences="The tested RBAC boundary prevented a state-changing action from a read-only role.",
        assumptions="The production deployment preserves the same role binding for analyst accounts.",
        contradictions="None observed.",
        gaps="No issues remained within the declared review scope.",
        technical_sufficiency="sufficient",
        reachability_sufficiency="sufficient",
        mission_sufficiency="sufficient",
        conclusion="meets",
        scenario_state="not_demonstrated",
        confidence="high",
        required_action="accept",
        priority="routine",
        scope_boundary="Conclusion applies to the tested telemetry API role mapping and command endpoint authorization logic.",
        rationale="The analyst token failed to invoke the protected action and the denial was logged.",
        recommendations="Retest after role-template changes.\nKeep denied-command logging enabled.",
        acceptance_criteria="Read-only roles remain unable to invoke state-changing endpoints.",
        status="closed",
    )
    ev1 = add_evidence(
        clock,
        investigation,
        filename="rbac_api_check.txt",
        description="API role test showing a denied command attempt for the analyst token.",
        body="""
        token_role: analyst
        telemetry_read: allowed
        command_post: denied
        audit_event: recorded
        """,
    )
    add_finding(
        clock,
        investigation,
        title="Read-only telemetry role respected by command endpoint",
        state="verified_closed",
        condition_text="The analyst token is blocked from state-changing API actions.",
        observed_effect="The protected endpoint returns a denial and emits an audit event.",
        credible_impact="The tested role boundary reduces the chance of accidental command issuance from read-only users.",
        mapping_state="confirmed",
        mapping_rationale="The observed access decision is directly tied to the tested claim.",
    )
    profile = seed_spd5_companion(assessment)
    db.session.add(profile)
    apply_companion(
        profile,
        scenario="evidence_backed_alignment",
        summary="The reviewed cloud control path aligns well with the expected authorization and audit controls.",
        notes="Good cloud-segment reference case for Meets plus Not Demonstrated.",
        statuses={
            "SPD5-GOV-01": "implemented",
            "SPD5-GOV-02": "implemented",
            "SPD5-GOV-04": "implemented",
            "SPD5-GRD-01": "implemented",
            "SPD5-GRD-02": "implemented",
            "SPD5-GRD-03": "implemented",
            "SPD5-GRD-04": "implemented",
            "SPD5-GRD-05": "implemented",
            "SPD5-MON-02": "implemented",
            "SPD5-MON-03": "implemented",
            "SPD5-MON-04": "implemented",
        },
        refs={
            "SPD5-GRD-02": investigation.fari_id,
            "SPD5-GRD-03": f"{investigation.fari_id}, {ev1.fari_id}",
        },
    )
    capture_version(
        clock,
        assessment,
        summary="Cloud RBAC review closed as Meets for the declared API path.",
        trigger="assessment_closed",
    )
    return SeedCase(
        assessment=assessment,
        investigation=investigation,
        profile=profile,
        current_result=investigation.conclusion,
        current_scenario=investigation.scenario_state,
        companion_scenario=profile.scenario,
        posture=profile.posture,
        versions=[("v1", "RBAC and audit controls confirmed on the telemetry API path.")],
        notes="Primary cloud reference for a clean success case.",
    )


def seed_case_05(clock: Clock) -> SeedCase:
    assessment = create_assessment(
        clock,
        client_name="Orion ADCS Integrators",
        title="Third-Party Firmware Intake",
        mission_context="Supplier firmware intake before the next hardware-in-the-loop campaign.",
        scope="Vendor package receipt, checksum review, and available provenance artifacts.",
        authorization="Supplier-package normalization by the internal report author.",
        exclusions="No binary reverse engineering and no secure-boot retest in this initial intake.",
        status="draft",
        maturity="provisional",
    )
    asset = add_asset(
        clock,
        assessment,
        name="ADCS Vendor Firmware Bundle",
        segment="supply_chain",
        description="Supplier-delivered firmware package for the ADCS control board.",
        access_model="black_box",
        coverage="reviewed",
    )
    investigation = add_investigation(
        clock,
        assessment,
        asset,
        title="Firmware provenance intake",
        claim_description="Only validated third-party firmware images can be promoted to integration.",
        gating=False,
        technical_reporter="Supplier Assurance Desk",
        method="Document intake and package normalization only.",
        environment="Offline review of the received vendor package and checksum sheet.",
        facts="A firmware archive and checksum sheet were received.\nNo signed manifest was supplied.\nNo secure-boot validation evidence was attached.",
        assertions="The vendor states the package matches the latest qualified release.",
        inferences="The available material is not enough to support a promotion decision.",
        assumptions="Additional supplier evidence may exist but was not part of the intake package.",
        contradictions="The release note references a signature process, but no signature artifact was delivered.",
        gaps="No signed manifest.\nNo provenance chain.\nNo secure-boot validation evidence.\nNo integration retest yet.",
        technical_sufficiency="insufficient",
        reachability_sufficiency="insufficient",
        mission_sufficiency="insufficient",
        conclusion="not_assessed",
        scenario_state="not_evaluated",
        confidence="low",
        required_action="extend_investigation",
        priority="planned",
        scope_boundary="This intake record applies only to the received supplier package and supporting documents.",
        rationale="The report author has not received enough evidence to evaluate the promotion claim.",
        recommendations="Request a signed manifest.\nRequest secure-boot validation evidence.\nSchedule bench validation before promotion.",
        acceptance_criteria="The package includes provenance artifacts and passes the planned validation gate.",
        status="draft",
    )
    ev1 = add_evidence(
        clock,
        investigation,
        filename="vendor_intake_note.txt",
        description="Normalized intake note for the received firmware bundle.",
        body="""
        package_name: adcs_fw_3_7_bundle.zip
        signed_manifest: absent
        secure_boot_evidence: absent
        promotion_decision: blocked_pending_supplier_material
        """,
    )
    add_finding(
        clock,
        investigation,
        title="Supplier package lacks promotion evidence",
        state="candidate",
        condition_text="The received firmware bundle lacks the provenance material needed for a promotion decision.",
        observed_effect="The package can be tracked, but not yet accepted into the integration baseline.",
        credible_impact="Unverified supplier firmware could enter the mission build path if governance is weak.",
        mapping_state="candidate",
        mapping_rationale="This is an intake-stage control weakness, not yet a confirmed exploitation path.",
    )
    profile = seed_spd5_companion(assessment)
    db.session.add(profile)
    apply_companion(
        profile,
        scenario="supplier_attestation_pending",
        summary="The supplier package is known and tracked, but the core trust artifacts are still missing.",
        notes="Deliberately left as a draft, non-gating case so the workspace contains a genuine Not Assessed record.",
        statuses={
            "SPD5-GOV-01": "implemented",
            "SPD5-SUP-01": "implemented",
            "SPD5-SUP-02": "not_verified",
            "SPD5-SUP-03": "implemented",
            "SPD5-SUP-04": "not_verified",
            "SPD5-SPC-03": "not_verified",
            "SPD5-SPC-04": "not_verified",
        },
        refs={
            "SPD5-SUP-01": f"{investigation.fari_id}, {ev1.fari_id}",
            "SPD5-SUP-02": investigation.fari_id,
        },
    )
    capture_version(
        clock,
        assessment,
        summary="Supplier package intake recorded; validation remains pending.",
    )
    return SeedCase(
        assessment=assessment,
        investigation=investigation,
        profile=profile,
        current_result=investigation.conclusion,
        current_scenario=investigation.scenario_state,
        companion_scenario=profile.scenario,
        posture=profile.posture,
        versions=[("v1", "Intake-only snapshot with a real Not Assessed outcome.")],
        notes="Non-gating draft case used to exercise the Not Assessed portfolio state and supplier-pending overlay.",
    )


def seed_case_06(clock: Clock) -> SeedCase:
    assessment = create_assessment(
        clock,
        client_name="Pioneer Flight Software",
        title="SBOM Vulnerability Lifecycle",
        mission_context="Software supply-chain review for the mission image build before final release freeze.",
        scope="Build SBOM, vulnerable dependency handling, and fix verification through refreshed inventory.",
        authorization="Internal software assurance review with retained SBOM exports.",
        exclusions="No source-level exploit development and no vendor mirror compromise simulation.",
        status="draft",
        maturity="provisional",
    )
    asset = add_asset(
        clock,
        assessment,
        name="Mission Image Build Pipeline",
        segment="supply_chain",
        description="Pipeline that assembles the flight-support image and dependency set.",
        access_model="grey_box",
        coverage="tested",
    )
    investigation = add_investigation(
        clock,
        assessment,
        asset,
        title="Known vulnerable dependency present in build output",
        claim_description="Mission image builds exclude components with known high-confidence vulnerable versions.",
        gating=True,
        technical_reporter="Software Assurance",
        method="SBOM review, package verification, and post-fix inventory comparison.",
        environment="Controlled CI export and local SBOM correlation.",
        facts="The initial SBOM listed libfoo version 1.4.2.\nThe review mapped libfoo 1.4.2 to an open high-severity advisory.\nThe vulnerable version remained in the image at the time of the first snapshot.",
        assertions="The vulnerable branch was only used by a support utility, not the command loop.",
        inferences="The build process did not yet enforce the intended dependency exclusion rule.",
        assumptions="The advisory mapping remains valid for the listed package and version.",
        contradictions="None observed in the supplied build inventory.",
        gaps="No proof yet that the upgraded package has been built and retested.",
        technical_sufficiency="sufficient",
        reachability_sufficiency="partial",
        mission_sufficiency="partial",
        conclusion="does_not_meet",
        scenario_state="plausible",
        confidence="high",
        required_action="remediate",
        priority="immediate",
        scope_boundary="Conclusion applies to the reviewed build output and its supplied SBOM records.",
        rationale="The baseline image still contained a dependency version mapped to a known advisory.",
        recommendations="Upgrade libfoo to a fixed release.\nRefresh the SBOM and verify the build output.",
        acceptance_criteria="The refreshed SBOM no longer contains the vulnerable version and the fix is verified.",
        status="ready",
    )
    ev1 = add_evidence(
        clock,
        investigation,
        filename="baseline_sbom_review.txt",
        description="Baseline SBOM review tying libfoo 1.4.2 to a known advisory.",
        body="""
        component: libfoo
        version: 1.4.2
        advisory: CVE-2026-0001
        build_status: vulnerable_version_present
        """,
    )
    finding = add_finding(
        clock,
        investigation,
        title="Baseline image contains a vulnerable dependency version",
        state="confirmed",
        condition_text="libfoo 1.4.2 is present in the baseline image and matches a tracked advisory.",
        observed_effect="The dependency inventory violates the exclusion claim at the time of review.",
        credible_impact="A known vulnerable package remains in the mission-support build path.",
        mapping_state="confirmed",
        mapping_rationale="The evidence directly ties the image inventory to the reviewed advisory.",
    )
    baseline_sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"component": {"name": "mission-image", "version": "2026.06.0"}},
        "components": [
            {"name": "libfoo", "version": "1.4.2", "purl": "pkg:generic/libfoo@1.4.2"},
            {"name": "orbital-utils", "version": "5.2.1", "purl": "pkg:generic/orbital-utils@5.2.1"},
        ],
    }
    baseline_doc = add_sbom_document(
        clock,
        assessment,
        asset,
        filename="baseline-image-sbom.json",
        payload=baseline_sbom,
        file_format="cyclonedx",
        notes="Baseline image inventory before dependency remediation.",
    )
    component = add_inventory_component(
        clock,
        assessment,
        asset,
        baseline_doc,
        name="libfoo",
        ecosystem="generic",
        version="1.4.2",
        status="tracked",
        purl="pkg:generic/libfoo@1.4.2",
        component_type="library",
        license_name="BSD-3-Clause",
        notes="Tracked through the mission image SBOM lifecycle.",
    )
    add_inventory_event(
        clock,
        component,
        baseline_doc,
        event_type="imported",
        summary="Baseline SBOM imported into the FARI inventory timeline.",
        status_after="tracked",
        to_version="1.4.2",
    )
    add_inventory_event(
        clock,
        component,
        baseline_doc,
        event_type="vulnerability_detected",
        summary="Known advisory mapped to libfoo 1.4.2 during the baseline review.",
        status_after="vulnerable",
        from_version="1.4.2",
        to_version="1.4.2",
        vulnerability_id="CVE-2026-0001",
        severity="high",
    )
    profile = seed_spd5_companion(assessment)
    db.session.add(profile)
    apply_companion(
        profile,
        scenario="continuous_assurance",
        summary="The build process is being tracked as a living supply-chain baseline with SBOM evidence.",
        notes="This case exists to exercise both the inventory timeline and the mitigation traceability flow.",
        statuses={
            "SPD5-GOV-01": "implemented",
            "SPD5-GOV-02": "implemented",
            "SPD5-SUP-01": "implemented",
            "SPD5-SUP-02": "implemented",
            "SPD5-SUP-03": "implemented",
            "SPD5-SUP-04": "implemented",
            "SPD5-MON-03": "implemented",
            "SPD5-MON-04": "implemented",
        },
        refs={
            "SPD5-SUP-01": f"{investigation.fari_id}, {baseline_doc.fari_id}, {component.fari_id}",
            "SPD5-SUP-03": investigation.fari_id,
        },
    )
    capture_version(
        clock,
        assessment,
        summary="Initial SBOM review found a vulnerable dependency in the baseline image.",
    )

    refreshed_sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 2,
        "metadata": {"component": {"name": "mission-image", "version": "2026.06.1"}},
        "components": [
            {"name": "libfoo", "version": "1.4.5", "purl": "pkg:generic/libfoo@1.4.5"},
            {"name": "orbital-utils", "version": "5.2.1", "purl": "pkg:generic/orbital-utils@5.2.1"},
        ],
    }
    refresh_doc = add_sbom_document(
        clock,
        assessment,
        asset,
        filename="remediated-image-sbom.json",
        payload=refreshed_sbom,
        file_format="cyclonedx",
        notes="Refreshed image inventory after dependency remediation.",
    )
    add_inventory_event(
        clock,
        component,
        refresh_doc,
        event_type="version_updated",
        summary="libfoo updated in the mission image build after remediation.",
        status_after="update_in_progress",
        from_version="1.4.2",
        to_version="1.4.5",
    )
    add_inventory_event(
        clock,
        component,
        refresh_doc,
        event_type="fix_verified",
        summary="The refreshed SBOM and build output confirm that the fixed dependency replaced the vulnerable one.",
        status_after="fixed",
        from_version="1.4.2",
        to_version="1.4.5",
    )
    add_evidence(
        clock,
        investigation,
        filename="remediated_sbom_review.txt",
        description="Refreshed SBOM review confirming the fixed dependency version.",
        body="""
        component: libfoo
        previous_version: 1.4.2
        current_version: 1.4.5
        advisory_status: fixed_version_confirmed
        """,
    )
    finding.state = "verified_closed"
    finding.condition_text = "The vulnerable baseline dependency was removed from the refreshed image."
    finding.observed_effect = "The current SBOM shows libfoo 1.4.5 instead of 1.4.2."
    finding.credible_impact = "The reviewed advisory no longer maps to the current build output."
    investigation.facts = (
        "The refreshed SBOM lists libfoo version 1.4.5.\n"
        "The inventory timeline records the update and fix verification.\n"
        "The vulnerable baseline version is no longer present in the reviewed build output."
    )
    investigation.gaps = "No unresolved dependency gap remained in the declared scope."
    investigation.reachability_sufficiency = "sufficient"
    investigation.mission_sufficiency = "sufficient"
    investigation.conclusion = "meets"
    investigation.scenario_state = "not_demonstrated"
    investigation.required_action = "accept"
    investigation.priority = "routine"
    investigation.rationale = (
        "The current build inventory no longer contains the vulnerable dependency version."
    )
    investigation.recommendations = (
        "Keep SBOM export mandatory for each mission image release.\n"
        "Record any future advisory mapping as an inventory event."
    )
    investigation.acceptance_criteria = (
        "Future builds continue to show the fixed dependency or a later accepted version."
    )
    investigation.status = "closed"
    investigation.updated_at = clock.tick()
    assessment.status = "closed"
    assessment.maturity = "final"
    apply_companion(
        profile,
        scenario="continuous_assurance",
        summary="The supply-chain control set now has a verified remediation trail tied to SBOM evidence.",
        notes="Use this case to demo the combination of FARI revisions and inventory events.",
        statuses={
            "SPD5-GOV-01": "implemented",
            "SPD5-GOV-02": "implemented",
            "SPD5-SUP-01": "implemented",
            "SPD5-SUP-02": "implemented",
            "SPD5-SUP-03": "implemented",
            "SPD5-SUP-04": "implemented",
            "SPD5-MON-03": "implemented",
            "SPD5-MON-04": "implemented",
        },
        refs={
            "SPD5-SUP-01": f"{investigation.fari_id}, {baseline_doc.fari_id}, {refresh_doc.fari_id}, {component.fari_id}",
            "SPD5-SUP-03": f"{investigation.fari_id}, {component.fari_id}",
            "SPD5-SUP-04": investigation.fari_id,
        },
    )
    capture_version(
        clock,
        assessment,
        summary="Refreshed SBOM verified the dependency remediation and closed the claim.",
        trigger="assessment_closed",
    )
    return SeedCase(
        assessment=assessment,
        investigation=investigation,
        profile=profile,
        current_result=investigation.conclusion,
        current_scenario=investigation.scenario_state,
        companion_scenario=profile.scenario,
        posture=profile.posture,
        versions=[
            ("v1", "Baseline image contains libfoo 1.4.2 with an open advisory."),
            ("v2", "SBOM refresh confirms libfoo 1.4.5 and closes the claim."),
        ],
        notes="Primary continuous-assurance example using SBOM, inventory events, and mitigation traceability.",
    )


def seed_case_07(clock: Clock) -> SeedCase:
    assessment = create_assessment(
        clock,
        client_name="Deep Range Rehearsal Team",
        title="Command-Link Confidentiality Rehearsal",
        mission_context="Rehearsal-environment review for a non-flight command link used during integration training.",
        scope="Rehearsal RF link, external line encryptor, and physical control envelope.",
        authorization="Lab-only review under the rehearsal network and RF controls.",
        exclusions="No claim is made about flight-link cryptography outside the rehearsal environment.",
        status="closed",
        maturity="final",
    )
    asset = add_asset(
        clock,
        assessment,
        name="Rehearsal Command Link",
        segment="link",
        description="Temporary command-link stack used in rehearsals with an external line encryptor.",
        access_model="grey_box",
        coverage="tested",
    )
    investigation = add_investigation(
        clock,
        assessment,
        asset,
        title="Confidentiality under compensating controls",
        claim_description="The rehearsal command link preserves command confidentiality within its declared operating envelope.",
        gating=True,
        technical_reporter="Systems Security Engineering",
        method="Architecture review, enclave inspection, and controlled rehearsal check.",
        environment="Shielded rehearsal chamber with an external line encryptor and isolated operator bench.",
        facts="The rehearsal radios rely on an external line encryptor.\nThe rehearsal enclosure is physically isolated.\nSession keys are rotated before each exercise window.",
        assertions="The encryptor policy is tied to the same operator checklist used by the rehearsal team.",
        inferences="The declared operating envelope preserves confidentiality even though the radio itself does not provide native encryption.",
        assumptions="The chamber and line-encryptor procedure remain in force for each rehearsal.",
        contradictions="None observed for the declared rehearsal scope.",
        gaps="The evidence does not extend to any environment outside the rehearsal enclosure.",
        technical_sufficiency="sufficient",
        reachability_sufficiency="partial",
        mission_sufficiency="partial",
        conclusion="meets",
        scenario_state="plausible",
        confidence="medium",
        required_action="accept",
        priority="routine",
        scope_boundary="Conclusion applies only to the declared rehearsal environment with the external encryptor and physical enclosure controls in place.",
        rationale="The tested scope used compensating controls that preserved confidentiality in the rehearsal operating envelope.",
        recommendations="Keep the encryptor pre-check mandatory.\nReassess if the rehearsal link is used outside the enclosed environment.",
        acceptance_criteria="The rehearsal setup continues to require the external encryptor and isolated enclosure for use.",
        status="closed",
    )
    ev1 = add_evidence(
        clock,
        investigation,
        filename="rehearsal_link_controls.txt",
        description="Summary of the compensating control set used for the rehearsal link.",
        body="""
        external_encryptor: enabled
        enclosure_state: shielded
        session_key_rotation: per_rehearsal_window
        radio_native_crypto: absent
        """,
    )
    add_finding(
        clock,
        investigation,
        title="Rehearsal confidentiality depends on compensating controls",
        state="accepted_risk",
        condition_text="The rehearsal radios depend on an external encryptor and physical isolation rather than native radio encryption.",
        observed_effect="Confidentiality is preserved only while the declared compensating controls remain in place.",
        credible_impact="Using the same link outside the enclosure would require a new conclusion.",
        mapping_state="confirmed",
        mapping_rationale="The tested scope and its limit are explicit in the supplied material.",
    )
    profile = seed_spd5_companion(assessment)
    db.session.add(profile)
    apply_companion(
        profile,
        scenario="compensating_controls",
        summary="The rehearsal scope meets its claim because external controls compensate for missing native radio encryption.",
        notes="Important example of FARI allowing a scoped Meets result without pretending the broader environment was proven secure.",
        statuses={
            "SPD5-GOV-01": "implemented",
            "SPD5-GOV-02": "implemented",
            "SPD5-COM-03": "implemented",
            "SPD5-COM-04": "implemented",
            "SPD5-COM-05": "implemented",
            "SPD5-GRD-05": "implemented",
        },
        refs={
            "SPD5-COM-05": f"{investigation.fari_id}, {ev1.fari_id}",
            "SPD5-GRD-05": investigation.fari_id,
        },
        control_notes={
            "SPD5-COM-05": "The direct radio control is replaced here by an external encryptor plus enclosure controls.",
        },
    )
    capture_version(
        clock,
        assessment,
        summary="Compensating-control review closed as Meets for the declared rehearsal envelope.",
        trigger="assessment_closed",
    )
    return SeedCase(
        assessment=assessment,
        investigation=investigation,
        profile=profile,
        current_result=investigation.conclusion,
        current_scenario=investigation.scenario_state,
        companion_scenario=profile.scenario,
        posture=profile.posture,
        versions=[("v1", "Scoped confidentiality result based on compensating controls.")],
        notes="Reference case for Meets plus Plausible and the compensating-controls companion scenario.",
    )


def render_catalog(cases: list[SeedCase]) -> None:
    scenario_labels = {item["slug"]: item["title"] for item in SPD5_SCENARIOS}
    lines = [
        "# FARI Scenario Test Catalog",
        "",
        "Seeded workspace catalog for the local FARI demo database.",
        "",
        "The workspace was reset and repopulated to cover the main FARI claim outcomes,",
        "scenario dispositions, mitigation traces, and SPD-5 companion-profile modes.",
        "",
        "## Coverage summary",
        "",
        "- `Does Not Meet`: present in current state and in initial mitigation snapshots.",
        "- `Meets`: present in clean success, mitigation-success, and compensating-control cases.",
        "- `Inconclusive`: present as a closed replay-characterization case.",
        "- `Not Assessed`: present as a draft non-gating intake case.",
        "- `Demonstrated`, `Plausible`, `Not Demonstrated`, and `Not Evaluated` are all represented.",
        "- Every seeded case includes an SPD-5 companion profile.",
        "",
        "## Assessments",
        "",
        "| Assessment | Current result | Scenario disposition | SPD-5 companion | Posture | Versions | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in cases:
        versions = "<br>".join(f"{label}: {summary}" for label, summary in item.versions)
        lines.append(
            f"| `{item.assessment.fari_id}` {item.assessment.title} | "
            f"`{item.current_result}` | `{item.current_scenario}` | "
            f"`{scenario_labels[item.companion_scenario]}` | `{item.posture}` | "
            f"{versions} | {item.notes} |"
        )
    lines.extend(
        [
            "",
            "## Filter expectations",
            "",
            "- Portfolio filters should show closed assessments in `meets`, `does_not_meet`, and `inconclusive`.",
            "- The draft intake case should keep a genuine `not_assessed` overall state because its investigation is non-gating.",
            "- Traceability comparisons should be most interesting on the MFA rollout, auth fallback, and SBOM lifecycle cases.",
            "",
            "## Suggested demo order",
            "",
            "1. `ASM-2026-0001` for a partial mitigation that still fails.",
            "2. `ASM-2026-0002` for a clean mitigation success.",
            "3. `ASM-2026-0003` for a defensible inconclusive result.",
            "4. `ASM-2026-0005` for a true draft intake and supplier-pending view.",
            "5. `ASM-2026-0006` for SBOM-driven continuous assurance.",
        ]
    )
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    reset_workspace()
    app = make_app()
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        clock = Clock(BASE_TIME)
        cases = [
            seed_case_01(clock),
            seed_case_02(clock),
            seed_case_03(clock),
            seed_case_04(clock),
            seed_case_05(clock),
            seed_case_06(clock),
            seed_case_07(clock),
        ]
        db.session.commit()
        render_catalog(cases)
        print(f"Seeded {len(cases)} assessments into {db.engine.url.render_as_string(hide_password=False)}")
        for item in cases:
            result = overall_conclusion(item.assessment.investigations)
            print(
                f"- {item.assessment.fari_id} | assessment={result} | "
                f"claim={item.current_result} | scenario={item.current_scenario} | "
                f"spd5={item.companion_scenario}/{item.posture}"
            )
        print(f"Catalog written to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
