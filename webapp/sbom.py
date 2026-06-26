"""SBOM parsing helpers for the FARI assessment inventory."""

from __future__ import annotations

import json
import re


def parse_sbom_bytes(filename: str, raw: bytes) -> dict:
    text = raw.decode("utf-8", errors="replace")
    stripped = text.strip()
    if not stripped:
        return {"format": "empty", "components": []}

    if filename.lower().endswith(".json") or stripped.startswith("{"):
        payload = json.loads(stripped)
        return _parse_json_sbom(payload)

    return _parse_text_sbom(stripped)


def _parse_json_sbom(payload: dict) -> dict:
    if payload.get("bomFormat") == "CycloneDX":
        return {
            "format": "cyclonedx",
            "components": _normalize_components(
                {
                    "name": item.get("name", ""),
                    "version": item.get("version", ""),
                    "purl": item.get("purl", ""),
                    "component_type": item.get("type", ""),
                    "license_name": _license_name(item.get("licenses", [])),
                    "ecosystem": ecosystem_from_purl(item.get("purl", "")),
                }
                for item in payload.get("components", [])
            ),
        }

    if payload.get("spdxVersion") or payload.get("packages"):
        return {
            "format": "spdx",
            "components": _normalize_components(
                {
                    "name": item.get("name", ""),
                    "version": item.get("versionInfo", ""),
                    "purl": _external_purl(item.get("externalRefs", [])),
                    "component_type": "package",
                    "license_name": item.get("licenseConcluded", "")
                    or item.get("licenseDeclared", ""),
                    "ecosystem": ecosystem_from_purl(
                        _external_purl(item.get("externalRefs", []))
                    ),
                }
                for item in payload.get("packages", [])
                if item.get("name")
            ),
        }

    if isinstance(payload.get("packages"), dict):
        return {
            "format": "package-lock",
            "components": _normalize_components(_packages_from_package_lock(payload)),
        }

    if isinstance(payload.get("dependencies"), dict):
        return {
            "format": "dependency-map",
            "components": _normalize_components(
                _walk_dependency_map(payload.get("dependencies", {}))
            ),
        }

    raise ValueError("Unsupported SBOM JSON format.")


def _packages_from_package_lock(payload: dict) -> list[dict]:
    components = []
    packages = payload.get("packages") or {}
    for path, item in packages.items():
        version = item.get("version", "")
        if not version:
            continue
        name = item.get("name") or _package_name_from_path(path)
        if not name:
            continue
        components.append(
            {
                "name": name,
                "version": version,
                "purl": "",
                "component_type": "package",
                "license_name": "",
                "ecosystem": "npm",
            }
        )
    if components:
        return components
    return list(_walk_dependency_map(payload.get("dependencies", {})))


def _walk_dependency_map(items: dict, seen: set | None = None):
    seen = seen or set()
    for name, item in items.items():
        version = item.get("version", "")
        key = (name, version)
        if key not in seen:
            seen.add(key)
            yield {
                "name": name,
                "version": version,
                "purl": "",
                "component_type": "package",
                "license_name": "",
                "ecosystem": "npm",
            }
        nested = item.get("dependencies") or {}
        if isinstance(nested, dict):
            yield from _walk_dependency_map(nested, seen)


def _parse_text_sbom(text: str) -> dict:
    components = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([-A-Za-z0-9_.+/]+)\s*(==|=|:|@)\s*([^\s#]+)$", line)
        if match:
            name, _operator, version = match.groups()
            components.append(
                {
                    "name": name,
                    "version": version,
                    "purl": "",
                    "component_type": "package",
                    "license_name": "",
                    "ecosystem": infer_text_ecosystem(name),
                }
            )
            continue
        tokens = line.split()
        if len(tokens) == 2:
            components.append(
                {
                    "name": tokens[0],
                    "version": tokens[1],
                    "purl": "",
                    "component_type": "package",
                    "license_name": "",
                    "ecosystem": infer_text_ecosystem(tokens[0]),
                }
            )
    if not components:
        raise ValueError("Unsupported SBOM text format.")
    return {"format": "text-list", "components": _normalize_components(components)}


def _normalize_components(items) -> list[dict]:
    unique = {}
    for item in items:
        name = (item.get("name") or "").strip()
        version = (item.get("version") or "").strip()
        if not name:
            continue
        key = ((item.get("ecosystem") or "generic").strip().lower(), name.lower())
        unique[key] = {
            "name": name,
            "version": version,
            "purl": (item.get("purl") or "").strip(),
            "component_type": (item.get("component_type") or "").strip(),
            "license_name": (item.get("license_name") or "").strip(),
            "ecosystem": (item.get("ecosystem") or "generic").strip().lower(),
        }
    return sorted(unique.values(), key=lambda item: (item["ecosystem"], item["name"].lower()))


def ecosystem_from_purl(purl: str) -> str:
    if not purl.startswith("pkg:"):
        return "generic"
    body = purl[4:]
    return body.split("/", 1)[0].split("@", 1)[0].strip().lower() or "generic"


def infer_text_ecosystem(name: str) -> str:
    if "/" in name or name.startswith("@"):
        return "npm"
    if re.search(r"[A-Z]", name):
        return "generic"
    return "python"


def _external_purl(items: list[dict]) -> str:
    for item in items or []:
        if item.get("referenceType") == "purl":
            return item.get("referenceLocator", "")
    return ""


def _license_name(items: list[dict]) -> str:
    for item in items or []:
        license_data = item.get("license") or {}
        if license_data.get("id"):
            return license_data["id"]
        if license_data.get("name"):
            return license_data["name"]
    return ""


def _package_name_from_path(path: str) -> str:
    if not path:
        return ""
    path = path.replace("\\", "/")
    if "node_modules/" in path:
        return path.rsplit("node_modules/", 1)[-1]
    return path
