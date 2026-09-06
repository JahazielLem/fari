"""Asset source parsing helpers for heterogeneous technical files."""

from __future__ import annotations

import json
import re


BINARY_EXTENSIONS = {
    ".bin", ".dat", ".raw", ".img", ".iso", ".elf", ".hex", ".ihex", ".srec",
    ".s19", ".uf2", ".fw", ".firmware", ".rom", ".dmp", ".core", ".mem",
    ".squashfs", ".jffs2", ".mtd", ".pcap", ".pcapng", ".cap", ".wav", ".flac",
    ".mp3", ".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".pdf", ".doc",
    ".docx", ".xls", ".xlsx", ".zip", ".gz", ".tgz", ".tar", ".7z", ".rar",
    ".sqlite", ".db", ".sigmf-data",
}
TEXT_EXTENSIONS = {
    ".txt", ".log", ".md", ".csv", ".tsv", ".yaml", ".yml", ".xml", ".html",
    ".json", ".jsonl", ".ndjson", ".sigmf-meta", ".ini", ".cfg", ".conf",
}


def parse_asset_source(filename: str, raw: bytes) -> dict:
    filename_lower = filename.lower()
    if filename_lower.endswith(".sigmf-meta"):
        return _parse_sigmf_metadata(raw)
    if filename_lower.endswith(".sigmf-data"):
        return {"format": "sigmf-data", "components": [], "record_count": 0}

    extension = _source_extension(filename_lower)
    if extension in BINARY_EXTENSIONS or _looks_binary(raw):
        return {
            "format": _format_for_extension(extension, "binary"),
            "components": [],
            "record_count": 0,
        }

    text = raw.decode("utf-8", errors="replace")
    stripped = text.strip()
    if not stripped:
        return {"format": "empty", "components": []}

    if filename_lower.endswith((".jsonl", ".ndjson")):
        return _parse_jsonl_document(stripped)

    if filename_lower.endswith(".json") or stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            if _looks_like_jsonl(stripped):
                return _parse_jsonl_document(stripped)
            raise
        if isinstance(payload, dict) and _is_sigmf_metadata(payload):
            return {"format": "sigmf-meta", "components": [], "record_count": 0}
        return _parse_json_inventory(payload)

    parsed = _parse_text_inventory(stripped)
    if parsed["components"]:
        return parsed
    return {
        "format": _format_for_extension(extension, "text"),
        "components": [],
        "record_count": len([line for line in stripped.splitlines() if line.strip()]),
    }


def _source_extension(filename: str) -> str:
    for compound in (".sigmf-meta", ".sigmf-data"):
        if filename.endswith(compound):
            return compound
    return "." + filename.rsplit(".", 1)[-1] if "." in filename else ""


def _format_for_extension(extension: str, fallback: str) -> str:
    return {
        ".csv": "csv",
        ".tsv": "tsv",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "doc",
        ".xlsx": "xlsx",
        ".xls": "xls",
        ".pcap": "pcap",
        ".pcapng": "pcapng",
        ".elf": "elf",
        ".hex": "hex",
        ".sigmf-meta": "sigmf-meta",
        ".sigmf-data": "sigmf-data",
    }.get(extension, fallback)


def _looks_binary(raw: bytes) -> bool:
    if not raw:
        return False
    if b"\x00" in raw[:8192]:
        return True
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _is_sigmf_metadata(payload: dict) -> bool:
    return any(key in payload for key in ("global", "captures", "annotations"))


def _parse_sigmf_metadata(raw: bytes) -> dict:
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid SigMF metadata: {exc}.") from exc
    if not isinstance(payload, dict) or not _is_sigmf_metadata(payload):
        raise ValueError("Invalid SigMF metadata: expected global, captures, or annotations.")
    return {"format": "sigmf-meta", "components": [], "record_count": 0}


def _looks_like_jsonl(text: str) -> bool:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and line.strip() != "\\"
    ]
    return len(lines) > 1 and all(line.startswith("{") for line in lines)


def _parse_jsonl_document(text: str) -> dict:
    records = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if line_number == 1:
            line = line.lstrip("\ufeff")
        # A trailing backslash is commonly introduced when JSONL is copied from
        # an escaped Markdown/code block. It is not a record and is safe to skip.
        if not line or line == "\\":
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            # Some exported/copied JSONL uses Markdown-style \_ escapes. They
            # are not valid JSON escapes, but repairing only that sequence keeps
            # the importer strict for every other malformed escape.
            repaired = line.replace(r"\_", "_")
            if repaired == line:
                raise ValueError(
                    f"Invalid JSONL at line {line_number}, column {exc.colno}: {exc.msg}."
                ) from exc
            try:
                record = json.loads(repaired)
            except json.JSONDecodeError as repaired_exc:
                raise ValueError(
                    f"Invalid JSONL at line {line_number}, column {repaired_exc.colno}: {repaired_exc.msg}."
                ) from repaired_exc
        if not isinstance(record, dict):
            raise ValueError(
                f"Invalid JSONL at line {line_number}: each record must be a JSON object."
            )
        records.append(record)

    if not records:
        raise ValueError("The JSONL file does not contain any JSON object records.")

    # JSONL is preserved as a structured source document. Only component-shaped
    # records are normalized into inventory rows; event logs remain downloadable
    # source material instead of being misrepresented as dependencies.
    if all(record.get("name") and record.get("version") for record in records):
        return {
            "format": "jsonl-components",
            "components": _normalize_components(records),
            "record_count": len(records),
        }
    return {"format": "jsonl", "components": [], "record_count": len(records)}


def _parse_json_inventory(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"format": "json", "components": [], "record_count": 0}
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

    return {"format": "json", "components": [], "record_count": 0}


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


def _parse_text_inventory(text: str) -> dict:
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
    return {
        "format": "text-list",
        "components": _normalize_components(components),
        "record_count": len(components),
    }


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
