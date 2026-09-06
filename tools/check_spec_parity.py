"""Check that the current specification contract matches the web contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webapp.asset_sources import BINARY_EXTENSIONS, _format_for_extension
from webapp.contract import CONTRACT
from webapp.meta import FARI_VERSION


MANIFEST = ROOT / "spec" / "current" / "fari.manifest.yml"
SCHEMA = ROOT / "spec" / "schema" / "fari-assessment.schema.json"
SPECIFICATION = ROOT / "spec" / "current" / "specification" / "FARI-SPECIFICATION.md"
COMPLETE_SPECIFICATION = (
    ROOT / "spec" / "current" / "specification" / "FARI-SPECIFICATION-COMPLETE.md"
)


def _manifest_list(text: str, key: str) -> list[str]:
    match = re.search(
        rf"(?m)^  {re.escape(key)}:\s*\n((?:    - .*\n)+)",
        text,
    )
    if not match:
        raise AssertionError(f"Manifest is missing web_contract.{key}.")
    return [line.strip()[2:].strip() for line in match.group(1).splitlines()]


def _normalized_markdown(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def check() -> list[str]:
    errors: list[str] = []
    manifest_text = MANIFEST.read_text(encoding="utf-8")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema_defs = schema["$defs"]

    if f"generated_with: FARI v{FARI_VERSION}" not in manifest_text:
        errors.append("Manifest generated_with does not match FARI_VERSION.")

    for key, expected in CONTRACT.items():
        try:
            actual = _manifest_list(manifest_text, key)
        except AssertionError as exc:
            errors.append(str(exc))
            continue
        if actual != list(expected):
            errors.append(f"Manifest web_contract.{key} differs from webapp.contract.CONTRACT.")

    schema_checks = {
        "assessment_statuses": schema["properties"]["assessment"]["properties"]["status"]["enum"],
        "maturity_values": schema["properties"]["assessment"]["properties"]["report_maturity"]["enum"],
        "asset_segments": schema_defs["asset"]["properties"]["segment"]["enum"],
        "access_basis": schema_defs["asset"]["properties"]["access_model"]["enum"],
        "coverage_values": schema_defs["asset"]["properties"]["coverage"]["enum"],
        "finding_states": schema_defs["finding"]["properties"]["state"]["enum"],
        "asset_source_formats": schema_defs["assetSource"]["properties"]["file_format"]["enum"],
        "inventory_statuses": schema_defs["inventoryComponent"]["properties"]["status"]["enum"],
        "inventory_event_types": schema_defs["inventoryEvent"]["properties"]["event_type"]["enum"],
        "severity_values": [
            value
            for value in schema_defs["inventoryEvent"]["properties"]["severity"]["enum"]
            if value
        ],
    }
    for key, actual in schema_checks.items():
        if actual != list(CONTRACT[key]):
            errors.append(f"Schema {key} differs from webapp.contract.CONTRACT.")

    if _normalized_markdown(SPECIFICATION) != _normalized_markdown(COMPLETE_SPECIFICATION):
        errors.append("The complete specification copy differs from the canonical specification.")

    current_spec = _normalized_markdown(SPECIFICATION)
    for value in CONTRACT["asset_source_formats"]:
        if f"`{value}`" not in current_spec:
            errors.append(f"Specification does not document asset source format {value!r}.")
    if re.search(r"(?i)sparta|spd-5|attack flow|sbom|sbm-", current_spec):
        errors.append("The current specification contains a removed integration term.")

    parser_formats = {
        _format_for_extension(extension, "binary")
        for extension in BINARY_EXTENSIONS
    }
    parser_formats.discard("binary")
    missing_parser_formats = sorted(parser_formats - set(CONTRACT["asset_source_formats"]))
    if missing_parser_formats:
        errors.append(
            "Parser emits formats absent from the contract: "
            + ", ".join(missing_parser_formats)
        )
    return errors


def main() -> int:
    errors = check()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("FARI specification/web contract parity: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
