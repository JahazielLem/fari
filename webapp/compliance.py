"""Compliance companion profiles that can sit alongside core FARI records."""

from __future__ import annotations

from collections import Counter, defaultdict

from webapp.db import ComplianceCheck, ComplianceProfile, next_sequence, now_iso


SPD5_COMPANION_KEY = "spd5-companion"
SPD5_COMPANION_TITLE = "SPD-5 companion checklist"
SPD5_COMPANION_FRAMEWORK = "Space Policy Directive-5"
SPD5_COMPANION_VERSION = "2020-09-04"
SPD5_COMPANION_REFERENCE_URL = (
    "https://www.transportation.gov/sites/dot.gov/files/2023-11/"
    "Memorandum%20on%20Space%20Policy%20Directive-5%E2%80%94"
    "Cybersecurity%20Principles%20for%20Space%20Systems.pdf"
)

SPD5_STATUS_OPTIONS = [
    "not_verified",
    "implemented",
    "partially_implemented",
    "planned",
    "not_implemented",
    "not_applicable",
]

SPD5_SCENARIOS = [
    {
        "slug": "evidence_backed_alignment",
        "title": "Evidence-backed alignment",
        "summary": "Controls are implemented and supported by concrete FARI evidence and claims.",
    },
    {
        "slug": "partial_alignment",
        "title": "Partial alignment",
        "summary": "Some controls are in place, while remaining items need staged completion or validation.",
    },
    {
        "slug": "compensating_controls",
        "title": "Compensating controls",
        "summary": "A direct control is absent, but alternative safeguards reduce the same mission exposure.",
    },
    {
        "slug": "inconclusive_scope_boundary",
        "title": "Inconclusive due to scope",
        "summary": "The assessment cannot support a clean compliance statement because access, environment, or evidence is limited.",
    },
    {
        "slug": "supplier_attestation_pending",
        "title": "Supplier attestation pending",
        "summary": "Third-party firmware, hosted systems, or external services require vendor-backed evidence before the control can be accepted.",
    },
    {
        "slug": "continuous_assurance",
        "title": "Continuous assurance",
        "summary": "The companion profile is used as a living control baseline with SBOM refresh, retest, and monitoring updates over time.",
    },
]

SPD5_CONTROLS = [
    {
        "family": "Governance",
        "control_id": "SPD5-GOV-01",
        "title": "Space system cybersecurity policy",
        "statement": "A cybersecurity policy exists for the assessed space system and its operational environment.",
        "alignment": "supporting",
        "principle": "P1 · Risk-based cybersecurity-informed engineering across the lifecycle.",
        "recommended_artifacts": "Frame, authorization, mission context, governance evidence",
    },
    {
        "family": "Governance",
        "control_id": "SPD5-GOV-02",
        "title": "Threat analysis performed",
        "statement": "A documented threat analysis was completed for the assessed scope.",
        "alignment": "direct",
        "principle": "P1 · Threat-informed engineering and risk-based design.",
        "recommended_artifacts": "Investigation rationale, evidence, source material",
    },
    {
        "family": "Governance",
        "control_id": "SPD5-GOV-03",
        "title": "SPARTA threat model completed",
        "statement": "A SPARTA-informed threat model exists for the mission or assessed asset set.",
        "alignment": "supporting",
        "principle": "P1 · Threat-informed engineering with mission-specific adversary modeling.",
        "recommended_artifacts": "Attack flow, SPARTA mappings, findings",
    },
    {
        "family": "Governance",
        "control_id": "SPD5-GOV-04",
        "title": "Incident response procedures",
        "statement": "Incident response and escalation procedures exist for cyber events affecting the assessed system.",
        "alignment": "supporting",
        "principle": "P2 · Retain or recover positive control during cyber incidents.",
        "recommended_artifacts": "Runbooks, evidence, recommendations, acceptance criteria",
    },
    {
        "family": "Ground Segment",
        "control_id": "SPD5-GRD-01",
        "title": "MFA for operators",
        "statement": "Operator access to relevant ground systems requires multi-factor authentication.",
        "alignment": "supporting",
        "principle": "P6 · Ground system protection and access hardening.",
        "recommended_artifacts": "Ground asset investigations, evidence, access reviews",
    },
    {
        "family": "Ground Segment",
        "control_id": "SPD5-GRD-02",
        "title": "RBAC implemented",
        "statement": "Ground systems enforce role-based access according to mission duties and least privilege.",
        "alignment": "supporting",
        "principle": "P4/P6 · Restrict unauthorized access to critical functions.",
        "recommended_artifacts": "Ground investigations, access evidence, findings",
    },
    {
        "family": "Ground Segment",
        "control_id": "SPD5-GRD-03",
        "title": "Command logging and auditability",
        "statement": "Telecommand generation, approval, and dispatch events are logged and auditable.",
        "alignment": "supporting",
        "principle": "P6/P7 · Ground protection with detection and audit visibility.",
        "recommended_artifacts": "Evidence, findings, monitoring investigations",
    },
    {
        "family": "Ground Segment",
        "control_id": "SPD5-GRD-04",
        "title": "SIEM integration",
        "statement": "Relevant mission ground logs are centralized or correlated through a SIEM or equivalent monitoring workflow.",
        "alignment": "supporting",
        "principle": "P7 · Detect malicious activity and investigate anomalies.",
        "recommended_artifacts": "Monitoring evidence, detections, incident runbooks",
    },
    {
        "family": "Ground Segment",
        "control_id": "SPD5-GRD-05",
        "title": "Network segmentation",
        "statement": "Ground networks are segmented so mission-critical paths are separated from less trusted environments.",
        "alignment": "direct",
        "principle": "P6 · Segregate space and ground infrastructure where practical.",
        "recommended_artifacts": "Architecture diagrams, evidence, attack paths",
    },
    {
        "family": "Space Segment",
        "control_id": "SPD5-SPC-01",
        "title": "Authenticated telecommands",
        "statement": "Telecommands are authenticated before being accepted by the target system.",
        "alignment": "direct",
        "principle": "P4 · Protect against unauthorized access to critical functions.",
        "recommended_artifacts": "Link or space investigations, evidence, findings",
    },
    {
        "family": "Space Segment",
        "control_id": "SPD5-SPC-02",
        "title": "Encrypted telecommands",
        "statement": "Telecommands are encrypted or otherwise protected against disclosure in transit.",
        "alignment": "direct",
        "principle": "P3/P4 · Preserve confidentiality and integrity of command paths.",
        "recommended_artifacts": "Link investigations, evidence, crypto design references",
    },
    {
        "family": "Space Segment",
        "control_id": "SPD5-SPC-03",
        "title": "Firmware integrity validation",
        "statement": "The platform validates firmware integrity before or during use.",
        "alignment": "supporting",
        "principle": "P3 · Maintain integrity of critical software and mission functions.",
        "recommended_artifacts": "Firmware review, SBOM, findings, evidence",
    },
    {
        "family": "Space Segment",
        "control_id": "SPD5-SPC-04",
        "title": "Secure boot",
        "statement": "Secure boot or an equivalent trust chain protects startup of mission-critical components.",
        "alignment": "supporting",
        "principle": "P3 · Integrity controls for critical software paths.",
        "recommended_artifacts": "Firmware investigations, evidence, supplier documentation",
    },
    {
        "family": "Space Segment",
        "control_id": "SPD5-SPC-05",
        "title": "Positive control recovery",
        "statement": "The mission defines a way to retain or recover positive control after a cyber event.",
        "alignment": "direct",
        "principle": "P2 · Retain or recover positive control.",
        "recommended_artifacts": "Response procedures, recommendations, scenario analysis",
    },
    {
        "family": "Space Segment",
        "control_id": "SPD5-SPC-06",
        "title": "Safe mode documented",
        "statement": "Safe mode behavior and cyber-relevant recovery assumptions are documented.",
        "alignment": "supporting",
        "principle": "P2 · Recovery planning for mission continuity.",
        "recommended_artifacts": "Mission context, runbooks, evidence, claims",
    },
    {
        "family": "Communications",
        "control_id": "SPD5-COM-01",
        "title": "Replay protection",
        "statement": "The mission implements freshness, nonce, sequence, or timing protections against replay.",
        "alignment": "direct",
        "principle": "P5 · Protect space-system communications against spoofing and replay-like abuse.",
        "recommended_artifacts": "Link investigations, evidence, findings, attack flows",
    },
    {
        "family": "Communications",
        "control_id": "SPD5-COM-02",
        "title": "Spoofing protection",
        "statement": "Relevant communication paths can reject or detect spoofed traffic, telemetry, or control data.",
        "alignment": "direct",
        "principle": "P5 · Protect against spoofing and malicious signal manipulation.",
        "recommended_artifacts": "Link or bus investigations, findings, SPARTA mappings",
    },
    {
        "family": "Communications",
        "control_id": "SPD5-COM-03",
        "title": "Cryptographic key management",
        "statement": "Cryptographic keys are generated, stored, rotated, and retired under a documented key-management process.",
        "alignment": "supporting",
        "principle": "P3/P4 · Protect confidentiality, integrity, and command trust anchors.",
        "recommended_artifacts": "Process evidence, recommendations, supplier documents",
    },
    {
        "family": "Communications",
        "control_id": "SPD5-COM-04",
        "title": "Credential rotation",
        "statement": "Operational credentials or shared secrets can be rotated in a planned and recoverable way.",
        "alignment": "supporting",
        "principle": "P4/P6 · Reduce long-term exposure of privileged access paths.",
        "recommended_artifacts": "Runbooks, evidence, acceptance criteria",
    },
    {
        "family": "Communications",
        "control_id": "SPD5-COM-05",
        "title": "RF link protection",
        "statement": "RF links include controls or operational procedures to reduce unauthorized interception, misuse, or interference.",
        "alignment": "direct",
        "principle": "P5 · Protect links from interference, spoofing, and unauthorized use.",
        "recommended_artifacts": "RF evidence, link investigations, monitoring outputs",
    },
    {
        "family": "Supply Chain",
        "control_id": "SPD5-SUP-01",
        "title": "Software inventory (SBOM)",
        "statement": "A maintained software inventory or SBOM exists for the assessed mission components.",
        "alignment": "supporting",
        "principle": "P8 · Manage supply chain risk with software visibility.",
        "recommended_artifacts": "SBOM documents, inventory timeline, component events",
    },
    {
        "family": "Supply Chain",
        "control_id": "SPD5-SUP-02",
        "title": "Third-party firmware validation",
        "statement": "Third-party firmware is reviewed, validated, or otherwise accepted through an explicit trust process.",
        "alignment": "direct",
        "principle": "P8 · Supply chain risk management for acquired components.",
        "recommended_artifacts": "Supplier evidence, firmware review, findings",
    },
    {
        "family": "Supply Chain",
        "control_id": "SPD5-SUP-03",
        "title": "Change control",
        "statement": "Mission-relevant software and firmware changes follow controlled approval and traceability procedures.",
        "alignment": "supporting",
        "principle": "P8 · Maintain disciplined change control for supplied software and updates.",
        "recommended_artifacts": "Version snapshots, SBOM events, evidence",
    },
    {
        "family": "Supply Chain",
        "control_id": "SPD5-SUP-04",
        "title": "Signed updates",
        "statement": "Software or firmware updates are signed or integrity-protected before deployment.",
        "alignment": "supporting",
        "principle": "P3/P8 · Preserve integrity of delivered updates and supply chain artifacts.",
        "recommended_artifacts": "Firmware evidence, supplier documentation, findings",
    },
    {
        "family": "Monitoring",
        "control_id": "SPD5-MON-01",
        "title": "RF anomaly detection",
        "statement": "The mission can detect or review anomalous RF behavior affecting protected links or services.",
        "alignment": "supporting",
        "principle": "P7 · Use detection methodologies for suspicious activity.",
        "recommended_artifacts": "RF monitoring evidence, alerts, investigations",
    },
    {
        "family": "Monitoring",
        "control_id": "SPD5-MON-02",
        "title": "Telemetry monitoring",
        "statement": "Telemetry relevant to mission cybersecurity is monitored and reviewed.",
        "alignment": "direct",
        "principle": "P7 · Detect anomalous behavior through telemetry and operational monitoring.",
        "recommended_artifacts": "Monitoring evidence, claims, findings",
    },
    {
        "family": "Monitoring",
        "control_id": "SPD5-MON-03",
        "title": "Critical event alerting",
        "statement": "Critical cyber-relevant events trigger alerts or escalation mechanisms.",
        "alignment": "supporting",
        "principle": "P7 · Detection, warning, and operational response.",
        "recommended_artifacts": "SIEM evidence, runbooks, recommendations",
    },
    {
        "family": "Monitoring",
        "control_id": "SPD5-MON-04",
        "title": "Post-incident forensic capability",
        "statement": "The mission can retain enough evidence to support post-incident reconstruction or forensics.",
        "alignment": "supporting",
        "principle": "P7/P2 · Detection plus recovery-oriented investigation support.",
        "recommended_artifacts": "Evidence handling, logging, inventory, procedures",
    },
]


def find_profile_by_key(assessment, profile_key: str) -> ComplianceProfile | None:
    for profile in assessment.compliance_profiles:
        if profile.profile_key == profile_key:
            return profile
    return None


def seed_spd5_companion(assessment) -> ComplianceProfile:
    sequence = next_sequence(assessment.compliance_profiles, "CPF")
    profile = ComplianceProfile(
        assessment=assessment,
        fari_id=f"CPF-{assessment.id:04d}-{sequence:03d}",
        profile_key=SPD5_COMPANION_KEY,
        title=SPD5_COMPANION_TITLE,
        framework_name=SPD5_COMPANION_FRAMEWORK,
        framework_version=SPD5_COMPANION_VERSION,
        scenario="inconclusive_scope_boundary",
        posture="not_started",
        summary="",
        notes="",
    )
    for index, definition in enumerate(SPD5_CONTROLS, start=1):
        profile.checks.append(
            ComplianceCheck(
                fari_id=f"CTL-{assessment.id:04d}-{index:03d}",
                control_id=definition["control_id"],
                family=definition["family"],
                title=definition["title"],
                control_statement=definition["statement"],
                spd5_alignment=definition["alignment"],
                principle_reference=definition["principle"],
                recommended_artifacts=definition["recommended_artifacts"],
                status="not_verified",
                sort_order=index,
            )
        )
    sync_profile_posture(profile)
    return profile


def sync_profile_posture(profile: ComplianceProfile) -> str:
    posture = derive_profile_posture(profile.checks)
    profile.posture = posture
    profile.updated_at = now_iso()
    return posture


def derive_profile_posture(checks) -> str:
    statuses = [check.status for check in checks if check.status != "not_applicable"]
    if not statuses or all(status == "not_verified" for status in statuses):
        return "not_started"
    if any(status == "not_implemented" for status in statuses):
        return "gap_identified"
    if any(status in {"partially_implemented", "planned"} for status in statuses):
        return "partially_aligned"
    if all(status == "implemented" for status in statuses):
        return "aligned"
    return "inconclusive"


def status_counts(checks) -> dict[str, int]:
    counts = Counter(check.status for check in checks)
    return {option: counts.get(option, 0) for option in SPD5_STATUS_OPTIONS}


def family_groups_for_profile(profile: ComplianceProfile) -> list[dict]:
    grouped = defaultdict(list)
    for check in sorted(profile.checks, key=lambda item: (item.family, item.sort_order, item.control_id)):
        grouped[check.family].append(check)
    families = []
    for family, checks in grouped.items():
        families.append(
            {
                "family": family,
                "checks": checks,
                "counts": status_counts(checks),
            }
        )
    return families


def scenario_by_slug(slug: str) -> dict | None:
    for scenario in SPD5_SCENARIOS:
        if scenario["slug"] == slug:
            return scenario
    return None
