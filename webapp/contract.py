"""Shared FARI contract values used by the web workflow and its templates."""

from __future__ import annotations


CONTRACT = {
    "assessment_statuses": ("draft", "closed"),
    "maturity_values": ("draft", "provisional", "final", "superseded"),
    "investigation_statuses": ("draft", "ready", "closed"),
    "asset_segments": ("space", "ground", "user", "link", "supply_chain", "cloud", "other"),
    "access_basis": ("private", "public", "other"),
    "coverage_values": ("not_assessed", "tested", "reviewed", "inferred", "out_of_scope"),
    "sufficiency_values": ("sufficient", "partial", "insufficient"),
    "conclusions": ("meets", "does_not_meet", "inconclusive", "not_assessed"),
    "scenario_states": ("demonstrated", "plausible", "not_demonstrated", "not_evaluated"),
    "confidence_values": ("high", "medium", "low"),
    "required_actions": ("accept", "remediate", "extend_investigation", "retest", "no_action"),
    "priority_values": ("immediate", "planned", "routine", "none"),
    "finding_states": ("candidate", "confirmed", "observation", "remediated", "verified_closed"),
    "mapping_states": ("candidate", "confirmed", "not_applicable"),
    "inventory_statuses": ("tracked", "vulnerable", "update_in_progress", "fixed", "accepted", "not_affected"),
    "inventory_event_types": ("imported", "vulnerability_detected", "version_updated", "fix_verified", "status_changed", "note"),
    "severity_values": ("critical", "high", "medium", "low", "info", "unknown"),
    "asset_source_formats": (
        "cyclonedx",
        "spdx",
        "package-lock",
        "dependency-map",
        "text-list",
        "jsonl",
        "jsonl-components",
        "sigmf-meta",
        "sigmf-data",
        "binary",
        "pcap",
        "pcapng",
        "elf",
        "hex",
        "csv",
        "tsv",
        "yaml",
        "xml",
        "pdf",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "text",
        "json",
        "empty",
    ),
}


CONCLUSION_ACTIONS = {
    "meets": frozenset(("accept", "no_action", "extend_investigation", "retest")),
    "does_not_meet": frozenset(("remediate", "extend_investigation", "retest")),
    "inconclusive": frozenset(("extend_investigation", "retest")),
    "not_assessed": frozenset(("extend_investigation", "no_action")),
}
