"""Parse the local SPARTA STIX catalog for UI lookup and report enrichment."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path


SPARTA_FILE = Path(
    os.environ.get(
        "FARI_SPARTA_FILE",
        Path(__file__).resolve().parent.parent / "sparta" / "sparta-attack-3.2.json",
    )
)


def _external_id(item: dict) -> str:
    for reference in item.get("external_references", []) or []:
        if reference.get("source_name") == "sparta" and reference.get("external_id"):
            return str(reference["external_id"])
    return ""


def _url(item: dict) -> str:
    for reference in item.get("external_references", []) or []:
        if reference.get("source_name") == "sparta" and reference.get("url"):
            return str(reference["url"])
    return ""


@lru_cache(maxsize=4)
def load_sparta_catalog(path: str | None = None) -> dict:
    source_path = Path(path) if path else SPARTA_FILE
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    objects = payload.get("objects", [])
    by_stix_id = {
        item["id"]: item
        for item in objects
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    ttps = {}
    countermeasures = {}
    version = ""
    for item in objects:
        if not isinstance(item, dict):
            continue
        external_id = _external_id(item)
        if item.get("type") == "x-sparta-collection":
            version = str(item.get("x_sparta_version") or item.get("version") or "")
        elif item.get("type") == "attack-pattern" and external_id:
            phases = item.get("kill_chain_phases", []) or []
            ttps[item["id"]] = {
                "id": external_id,
                "name": str(item.get("name") or external_id),
                "description": str(item.get("description") or ""),
                "phase": str(phases[0].get("phase_name") or "") if phases else "",
                "url": _url(item),
            }
        elif item.get("type") == "course-of-action" and external_id:
            countermeasures[item["id"]] = {
                "id": external_id,
                "name": str(item.get("name") or external_id),
                "description": str(item.get("description") or ""),
                "url": _url(item),
            }

    recommendations: dict[str, list[dict]] = {}
    for item in objects:
        if not isinstance(item, dict) or item.get("type") != "relationship":
            continue
        source_ref = item.get("source_ref")
        target = item.get("target_ref")
        if source_ref in countermeasures and target in ttps:
            recommendations.setdefault(ttps[target]["id"], []).append(
                countermeasures[source_ref]
            )

    ttp_items = sorted(ttps.values(), key=lambda item: (item["id"], item["name"]))
    for item in ttp_items:
        item["countermeasure_count"] = len(recommendations.get(item["id"], []))
    for ttp_id, items in recommendations.items():
        recommendations[ttp_id] = sorted(items, key=lambda item: (item["id"], item["name"]))
    return {
        "version": version,
        "ttps": ttp_items,
        "countermeasures_by_ttp": recommendations,
        "source": str(source_path),
        "object_count": len(by_stix_id),
    }


def search_ttps(query: str = "", limit: int = 20) -> list[dict]:
    normalized = query.strip().lower()
    items = load_sparta_catalog()["ttps"]
    if normalized:
        items = [
            item
            for item in items
            if normalized in item["id"].lower()
            or normalized in item["name"].lower()
            or normalized in item["description"].lower()
            or normalized in item["phase"].lower()
        ]
    return items[:limit]


def countermeasures_for(ttp_id: str) -> list[dict]:
    return load_sparta_catalog()["countermeasures_by_ttp"].get(ttp_id.strip(), [])
