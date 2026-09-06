"""Assessment snapshot, diff, and traceability helpers."""

from __future__ import annotations

import json

from webapp.db import AssessmentVersion
from webapp.reporting import human, overall_conclusion


ASSESSMENT_FIELDS = [
    "client_name",
    "title",
    "mission_context",
    "scope",
    "authorization",
    "exclusions",
    "status",
    "maturity",
    "report_author",
]

ASSET_FIELDS = ["name", "segment", "description", "access_model", "coverage"]
INVESTIGATION_FIELDS = [
    "title",
    "claim_id",
    "claim_description",
    "gating",
    "technical_reporter",
    "method",
    "environment",
    "technical_sufficiency",
    "reachability_sufficiency",
    "mission_sufficiency",
    "conclusion",
    "scenario_state",
    "confidence",
    "required_action",
    "priority",
    "scope_boundary",
    "rationale",
    "status",
]
ASSET_SOURCE_FIELDS = [
    "filename",
    "file_format",
    "component_count",
    "asset_fari_id",
    "sha256",
    "byte_size",
    "mime_type",
]
INVENTORY_FIELDS = [
    "name",
    "ecosystem",
    "current_version",
    "status",
    "asset_fari_id",
    "purl",
    "component_type",
    "license_name",
    "event_count",
    "latest_event_type",
]
HUMAN_VALUE_FIELDS = {
    "status",
    "maturity",
    "segment",
    "access_model",
    "coverage",
    "technical_sufficiency",
    "reachability_sufficiency",
    "mission_sufficiency",
    "conclusion",
    "scenario_state",
    "confidence",
    "required_action",
    "priority",
    "event_count",
    "latest_event_type",
    "file_format",
    "ecosystem",
}


def latest_revision_label(assessment) -> str:
    return f"v{assessment.revision_count}" if assessment.revision_count else "v0"


def build_assessment_snapshot(assessment) -> dict:
    return {
        "assessment": {
            **{field: getattr(assessment, field) for field in ASSESSMENT_FIELDS},
            "fari_id": assessment.fari_id,
            "revision_count": assessment.revision_count,
        },
        "overall_conclusion": overall_conclusion(assessment.investigations),
        "assets": [
            {
                "fari_id": asset.fari_id,
                **{field: getattr(asset, field) for field in ASSET_FIELDS},
            }
            for asset in assessment.assets
        ],
        "investigations": [
            {
                "fari_id": investigation.fari_id,
                "asset_fari_id": investigation.asset.fari_id if investigation.asset else "",
                "evidence_ids": [item.fari_id for item in investigation.evidence],
                "finding_ids": [item.fari_id for item in investigation.findings],
                **{
                    field: getattr(investigation, field)
                    for field in INVESTIGATION_FIELDS
                },
            }
            for investigation in assessment.investigations
        ],
        "asset_sources": [
            {
                "fari_id": document.fari_id,
                "asset_fari_id": document.asset.fari_id if document.asset else "",
                **{
                    field: getattr(document, field)
                    for field in (
                        "filename",
                        "file_format",
                        "component_count",
                        "sha256",
                        "byte_size",
                        "mime_type",
                    )
                },
            }
            for document in assessment.asset_sources
        ],
        "inventory_components": [
            {
                "fari_id": component.fari_id,
                "asset_fari_id": component.asset.fari_id if component.asset else "",
                "name": component.name,
                "ecosystem": component.ecosystem,
                "current_version": component.current_version,
                "status": component.status,
                "purl": component.purl,
                "component_type": component.component_type,
                "license_name": component.license_name,
                "notes": component.notes,
                "event_count": len(component.events),
                "latest_event_type": component.events[-1].event_type if component.events else "",
            }
            for component in assessment.inventory_components
        ],
    }


def capture_assessment_version(assessment, trigger: str, summary: str = "") -> AssessmentVersion:
    next_version = assessment.revision_count + 1
    assessment.revision_count = next_version
    version = AssessmentVersion(
        assessment=assessment,
        fari_id=f"VER-{assessment.id:04d}-{next_version:03d}",
        version_number=next_version,
        label=f"v{next_version}",
        trigger=trigger,
        summary=summary.strip(),
        snapshot_json=json.dumps(build_assessment_snapshot(assessment), sort_keys=True),
    )
    return version


def parse_version_snapshot(version: AssessmentVersion) -> dict:
    return json.loads(version.snapshot_json)


def current_snapshot_reference(assessment) -> dict:
    return {
        "id": "current",
        "label": "Current working state",
        "summary": "Live assessment state that has not necessarily been captured as a revision.",
        "created_at": assessment.updated_at,
        "trigger": "live_state",
        "snapshot": build_assessment_snapshot(assessment),
    }


def diff_snapshots(base_snapshot: dict, target_snapshot: dict) -> dict:
    groups = []
    groups.append(
        _compare_flat_group(
            "Assessment fields",
            "Assessment",
            base_snapshot.get("assessment", {}),
            target_snapshot.get("assessment", {}),
            ASSESSMENT_FIELDS + ["fari_id"],
        )
    )
    groups.append(
        _compare_collection_group(
            "Assets",
            base_snapshot.get("assets", []),
            target_snapshot.get("assets", []),
            ASSET_FIELDS,
        )
    )
    groups.append(
        _compare_collection_group(
            "Investigations",
            base_snapshot.get("investigations", []),
            target_snapshot.get("investigations", []),
            INVESTIGATION_FIELDS + ["asset_fari_id", "evidence_ids", "finding_ids"],
        )
    )
    groups.append(
        _compare_collection_group(
            "Asset sources",
            base_snapshot.get("asset_sources", []),
            target_snapshot.get("asset_sources", []),
            ASSET_SOURCE_FIELDS,
        )
    )
    groups.append(
        _compare_collection_group(
            "Inventory components",
            base_snapshot.get("inventory_components", []),
            target_snapshot.get("inventory_components", []),
            INVENTORY_FIELDS + ["notes"],
        )
    )
    groups = [group for group in groups if group["changes"]]
    total = sum(len(group["changes"]) for group in groups)
    return {"groups": groups, "total_changes": total}


def _compare_flat_group(title: str, item_label: str, before: dict, after: dict, fields: list[str]) -> dict:
    changes = []
    for field in fields:
        if before.get(field) != after.get(field):
            changes.append(
                    {
                        "kind": "changed",
                        "item": item_label,
                        "field": field,
                        "before": _serialize_value(field, before.get(field)),
                        "after": _serialize_value(field, after.get(field)),
                    }
                )
    return {"title": title, "changes": changes}


def _compare_collection_group(title: str, before_rows: list[dict], after_rows: list[dict], fields: list[str]) -> dict:
    before_map = {row["fari_id"]: row for row in before_rows}
    after_map = {row["fari_id"]: row for row in after_rows}
    changes = []
    for fari_id in sorted(set(before_map) | set(after_map)):
        if fari_id not in before_map:
            changes.append(
                {
                    "kind": "added",
                    "item": _item_label(after_map[fari_id]),
                    "field": "record",
                    "before": "",
                    "after": "Added in target state.",
                }
            )
            continue
        if fari_id not in after_map:
            changes.append(
                {
                    "kind": "removed",
                    "item": _item_label(before_map[fari_id]),
                    "field": "record",
                    "before": "Present in base state.",
                    "after": "Removed from target state.",
                }
            )
            continue
        before = before_map[fari_id]
        after = after_map[fari_id]
        for field in fields:
            if before.get(field) != after.get(field):
                changes.append(
                {
                    "kind": "changed",
                    "item": _item_label(after),
                    "field": field,
                    "before": _serialize_value(field, before.get(field)),
                    "after": _serialize_value(field, after.get(field)),
                }
            )
    return {"title": title, "changes": changes}


def _serialize_value(field: str, value) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "None"
    if value in ("", None):
        return "None"
    if isinstance(value, str) and field in HUMAN_VALUE_FIELDS:
        return human(value)
    return str(value)


def _item_label(item: dict) -> str:
    summary = item.get("title") or item.get("name") or item.get("filename") or item.get("fari_id")
    return f"{item.get('fari_id', 'record')} · {summary}"
