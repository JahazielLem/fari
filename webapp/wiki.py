"""Internal FARI wiki content derived from the canonical specification."""

from __future__ import annotations

import re
from functools import lru_cache
from html import escape
from pathlib import Path

from webapp.meta import FARI_VERSION


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_ROOT = PROJECT_ROOT / "spec"
SPEC_CURRENT_ROOT = SPEC_ROOT / "current"
SPEC_RELEASES_ROOT = SPEC_ROOT / "releases"


def _release_source_candidates(relative: str) -> list[Path]:
    candidates = [
        SPEC_RELEASES_ROOT / f"v{FARI_VERSION}" / "_sources" / relative,
        PROJECT_ROOT / "releases" / f"v{FARI_VERSION}" / "_sources" / relative,
    ]
    releases_root = SPEC_RELEASES_ROOT
    if releases_root.exists():
        for path in sorted(releases_root.glob("v*/_sources"), reverse=True):
            candidate = path / relative
            if candidate not in candidates:
                candidates.append(candidate)
    legacy_releases_root = PROJECT_ROOT / "releases"
    if legacy_releases_root.exists():
        for path in sorted(legacy_releases_root.glob("v*/_sources"), reverse=True):
            candidate = path / relative
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


SPEC_PATHS = [
    SPEC_CURRENT_ROOT / "specification" / "FARI-SPECIFICATION-COMPLETE.md",
    SPEC_CURRENT_ROOT / "specification" / "FARI-SPECIFICATION.md",
    *_release_source_candidates("specification/FARI-SPECIFICATION-COMPLETE.md"),
    *_release_source_candidates("specification/FARI-SPECIFICATION.md"),
    PROJECT_ROOT / "docs" / "FARI-SPECIFICATION-COMPLETE.md",
    PROJECT_ROOT / "docs" / "FARI-SPECIFICATION.md",
]

FALLBACK_SPEC_MARKDOWN = f"""# FARI specification

The canonical FARI specification is not available in this runtime.

## Workspace note

This FARI workspace is running without the versioned specification sources required by the internal wiki.

### Expected source

`spec/current/specification/FARI-SPECIFICATION-COMPLETE.md`

### Recovery guidance

Mount or copy the `spec` directory into the application runtime and reload the service.
"""

HELP_GUIDANCE = [
    {
        "title": "Client name",
        "section": "Frame",
        "body": (
            "Use the exact client, mission owner, program office, or business unit name that "
            "must appear in the executive report. Avoid nicknames or internal shorthand."
        ),
        "example": "Orbital Dynamics S.A. de C.V.",
        "keywords": ["client", "customer", "organization", "program owner"],
    },
    {
        "title": "Assessment title",
        "section": "Frame",
        "body": (
            "Write a short label that identifies the system and evaluation focus. A good title "
            "sounds like a report heading, not a vague project note."
        ),
        "example": "Ground telemetry API and mission operations workflow assessment",
        "keywords": ["title", "engagement", "assessment name"],
    },
    {
        "title": "Mission context",
        "section": "Frame",
        "body": (
            "State what the assessed system supports, where it operates, and why the result matters. "
            "The best entries connect the asset to a mission or business outcome."
        ),
        "example": (
            "Pre-launch validation of the hosted telemetry API used by mission operations for anomaly "
            "triage during spacecraft bus integration."
        ),
        "keywords": ["context", "mission", "why it matters", "operational role"],
    },
    {
        "title": "Scope",
        "section": "Frame",
        "body": (
            "List the exact assets, environments, interfaces, data paths, and access limits that are "
            "inside the assessment. If a reader cannot tell what was truly covered, the scope is too broad."
        ),
        "example": (
            "Hosted telemetry API, operator web console, and backend message broker in the staging "
            "environment; excludes production spacecraft commanding."
        ),
        "keywords": ["scope", "boundary", "in-scope", "included systems"],
    },
    {
        "title": "Authorization and safety constraints",
        "section": "Frame",
        "body": (
            "Capture the approvals, rules of engagement, stop conditions, prohibited actions, and "
            "safety limits that made the work legitimate."
        ),
        "example": (
            "Authorized staging-only testing approved by mission IT; no RF transmission, no credential "
            "reset, and stop immediately if operator workflows are disrupted."
        ),
        "keywords": ["authorization", "rules of engagement", "safety", "constraints"],
    },
    {
        "title": "Explicit exclusions",
        "section": "Frame",
        "body": (
            "Document what the assessment must not be interpreted as covering. This protects the final "
            "report from being read as evidence for systems, environments, or behaviors that were never evaluated."
        ),
        "example": "No on-orbit behavior, no physical actuator validation, and no supplier internal network review.",
        "keywords": ["exclusions", "out of scope", "limits"],
    },
    {
        "title": "Asset segment",
        "section": "Frame",
        "body": (
            "Choose the segment where the exposure primarily exists. Use `Other` when the asset spans "
            "multiple segments equally or does not fit the predefined categories cleanly."
        ),
        "example": "Select `Other` for a hybrid orchestration layer that coordinates cloud, ground, and user workflows.",
        "keywords": ["segment", "space", "ground", "link", "user", "supply chain", "cloud", "other"],
    },
    {
        "title": "Access basis",
        "section": "Frame",
        "body": (
            "Describe how the assessed access was obtained. `Public` covers internet exposure, OSINT, "
            "partner material, third-party disclosures, or information obtainable without controlled "
            "internal access. `Private` covers authorized internal, lab, source, or restricted access. "
            "`Other` covers mixed or atypical access paths."
        ),
        "example": (
            "Use `Public` for vendor documentation plus exposed endpoints, `Private` for a FlatSat lab "
            "with granted operator access, and `Other` for blended supplier and internal material."
        ),
        "keywords": ["access", "public", "private", "other", "osint", "third-party", "authorized"],
    },
    {
        "title": "Claim description",
        "section": "Frame",
        "body": (
            "Write the expected secure behavior being evaluated. Claims should be narrow, testable, and "
            "specific enough that Meets, Does Not Meet, or Inconclusive answer something concrete."
        ),
        "example": "The monitor rejects forged reply-like frames before presenting them as trusted state.",
        "keywords": ["claim", "expected behavior", "hypothesis"],
    },
    {
        "title": "Technical reporter",
        "section": "Frame",
        "body": (
            "Name the person or team that produced the technical material. This is the evidence producer, "
            "not the FARI report author."
        ),
        "example": "External RF assessment team",
        "keywords": ["technical reporter", "auditor", "evidence producer"],
    },
    {
        "title": "Method",
        "section": "Frame",
        "body": (
            "State how the evidence was obtained. The method can be intrusive or non-intrusive: fuzzing, "
            "OSINT correlation, supplier document review, source analysis, replay testing, or lab validation."
        ),
        "example": "OSINT corroboration plus staged API request replay in a customer-provided test tenant.",
        "keywords": ["method", "osint", "review", "testing", "validation"],
    },
    {
        "title": "Environment",
        "section": "Frame",
        "body": (
            "Describe where the observations came from so later readers understand the operational distance "
            "from reality: production, staging, FlatSat, emulator, document-only review, or mixed."
        ),
        "example": "Customer staging tenant backed by representative mission middleware and synthetic telemetry.",
        "keywords": ["environment", "lab", "staging", "production", "flatsat", "emulator"],
    },
    {
        "title": "Evidence-backed facts",
        "section": "Acquire",
        "body": (
            "Facts should say only what the preserved material directly supports. Save interpretation for "
            "inferences and keep each fact small enough to be traced back to one or more evidence items."
        ),
        "example": "HTTP response returned status 200 and included an unsigned telemetry payload.",
        "keywords": ["facts", "evidence", "observations"],
    },
    {
        "title": "Scope boundary",
        "section": "Inform",
        "body": (
            "State the exact limit of the conclusion. This is where you prevent a lab-only result, a "
            "document-only review, or a single-interface finding from being overstated."
        ),
        "example": "Conclusion applies only to the staging telemetry API and does not establish reachability from mission RF links.",
        "keywords": ["scope boundary", "limit of conclusion", "boundary"],
    },
    {
        "title": "Conclusion rationale",
        "section": "Inform",
        "body": (
            "Explain why the available evidence resolves, or fails to resolve, the declared claim. Keep "
            "the reasoning short, evidence-based, and explicit about uncertainty when the result is inconclusive."
        ),
        "example": "Observed replay acceptance demonstrates the claim does not hold for the tested API path.",
        "keywords": ["rationale", "conclusion", "reasoning", "why"],
    },
]


@lru_cache(maxsize=1)
def resolve_specification_path() -> Path | None:
    for path in SPEC_PATHS:
        if path.exists():
            return path
    return None


@lru_cache(maxsize=1)
def load_specification_markdown() -> str:
    spec_path = resolve_specification_path()
    if spec_path is None:
        return FALLBACK_SPEC_MARKDOWN.strip()
    return spec_path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def load_specification_outline() -> list[dict]:
    outline = []
    for line in load_specification_markdown().splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            outline.append({"level": 2, "title": title, "anchor": _slugify(title)})
        elif line.startswith("### "):
            title = line[4:].strip()
            outline.append({"level": 3, "title": title, "anchor": _slugify(title)})
    return outline


@lru_cache(maxsize=1)
def load_specification_html() -> str:
    return _render_markdown(load_specification_markdown())


@lru_cache(maxsize=1)
def glossary_definitions() -> list[tuple[str, str]]:
    body = _extract_section(load_specification_markdown(), "Glossary")
    items = []
    for match in re.finditer(
        r"^### (?P<term>.+?)\n(?P<body>.*?)(?=^### |\Z)", body, re.MULTILINE | re.DOTALL
    ):
        term = match.group("term").strip()
        block = match.group("body").strip()
        paragraph = block.split("\n\n", 1)[0]
        definition = " ".join(line.strip() for line in paragraph.splitlines()).strip()
        if term and definition:
            items.append((term, definition))
    return items


def search_definitions(query: str) -> list[dict]:
    entries = help_entries()
    needle = (query or "").strip().lower()
    if not needle:
        return entries[:24]

    tokens = [token for token in re.split(r"\s+", needle) if token]
    matches: list[tuple[int, str, dict]] = []
    for entry in entries:
        score = _entry_score(entry, tokens)
        if score:
            matches.append((score, entry["title"].lower(), entry))
    matches.sort(key=lambda item: (-item[0], item[1]))
    return [entry for _score, _title, entry in matches[:30]]


@lru_cache(maxsize=1)
def help_entries() -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()

    def add_entry(entry: dict):
        key = entry["title"].strip().lower()
        if not key or key in seen:
            return
        seen.add(key)
        entries.append(entry)

    for item in HELP_GUIDANCE:
        add_entry(_help_entry(**item))

    for item in specification_help_sections():
        add_entry(item)

    for term, definition in glossary_definitions():
        add_entry(
            _help_entry(
                title=term,
                section="Glossary",
                body=definition,
                kind="glossary",
                keywords=[term],
            )
        )

    return entries


@lru_cache(maxsize=1)
def specification_help_sections() -> list[dict]:
    markdown = load_specification_markdown()
    entries: list[dict] = []
    current_section: str | None = None
    current_section_lines: list[str] = []
    current_subsection: str | None = None
    current_subsection_lines: list[str] = []

    def flush_subsection():
        nonlocal current_subsection, current_subsection_lines
        if current_subsection:
            body = _plain_markdown_excerpt("\n".join(current_subsection_lines))
            if body:
                entries.append(
                    _help_entry(
                        title=current_subsection,
                        section=current_section or "Specification",
                        body=body,
                        kind="field",
                    )
                )
        current_subsection = None
        current_subsection_lines = []

    def flush_section():
        nonlocal current_section, current_section_lines
        if current_section:
            body = _plain_markdown_excerpt("\n".join(current_section_lines))
            if body:
                entries.append(
                    _help_entry(
                        title=current_section,
                        section="Specification",
                        body=body,
                        kind="section",
                    )
                )
        current_section = None
        current_section_lines = []

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            flush_subsection()
            flush_section()
            current_section = line[3:].strip()
            current_section_lines = []
            continue
        if line.startswith("### "):
            flush_subsection()
            current_subsection = line[4:].strip()
            current_subsection_lines = []
            continue
        if current_section is not None:
            current_section_lines.append(raw)
        if current_subsection is not None:
            current_subsection_lines.append(raw)

    flush_subsection()
    flush_section()
    return entries


def _help_entry(
    title: str,
    section: str,
    body: str,
    example: str = "",
    keywords: list[str] | None = None,
    kind: str = "guide",
) -> dict:
    anchor = _slugify(title)
    normalized_body = " ".join(body.split())
    normalized_example = " ".join(example.split())
    return {
        "term": title,
        "definition": normalized_body,
        "title": title,
        "section": section,
        "body": normalized_body,
        "example": normalized_example,
        "anchor": anchor,
        "href": f"/wiki#{anchor}",
        "kind": kind,
        "keywords": keywords or [],
    }


def _entry_score(entry: dict, tokens: list[str]) -> int:
    haystacks = {
        "title": entry["title"].lower(),
        "section": entry["section"].lower(),
        "body": entry["body"].lower(),
        "example": entry["example"].lower(),
        "keywords": " ".join(entry.get("keywords", [])).lower(),
    }
    score = 0
    for token in tokens:
        if token in haystacks["title"]:
            score += 7
        if token in haystacks["section"]:
            score += 4
        if token in haystacks["keywords"]:
            score += 4
        if token in haystacks["example"]:
            score += 3
        if token in haystacks["body"]:
            score += 2
    return score


def _plain_markdown_excerpt(block: str, max_paragraphs: int = 2, max_chars: int = 560) -> str:
    paragraphs: list[str] = []
    current: list[str] = []

    def flush():
        nonlocal current
        if current:
            paragraphs.append(" ".join(current).strip())
            current = []

    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            flush()
            if len(paragraphs) >= max_paragraphs:
                break
            continue
        if line.startswith("#"):
            continue
        cleaned = re.sub(r"^[-*]\s+", "", line)
        cleaned = re.sub(r"^\d+\.\s+", "", cleaned)
        current.append(cleaned)
    flush()
    text = _plain_inline(" ".join(paragraphs[:max_paragraphs]))
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."
    return text.strip()


def _plain_inline(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    return " ".join(text.split())


def _extract_section(markdown: str, title: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(title)}\n(?P<body>.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
    )
    match = pattern.search(markdown)
    return match.group("body").strip() if match else ""


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return value.strip("-") or "section"


def _render_markdown(markdown: str) -> str:
    lines = markdown.splitlines()
    html = []
    paragraph = []
    list_items = []
    list_type = None
    in_code = False
    code_lines = []
    quote_lines = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            html.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list():
        nonlocal list_items, list_type
        if not list_items:
            return
        tag = "ol" if list_type == "ol" else "ul"
        html.append(f"<{tag}>")
        for item in list_items:
            html.append(f"<li>{_inline(item)}</li>")
        html.append(f"</{tag}>")
        list_items = []
        list_type = None

    def flush_code():
        nonlocal in_code, code_lines
        if in_code:
            html.append(
                "<pre><code>"
                + escape("\n".join(code_lines)).strip()
                + "</code></pre>"
            )
            in_code = False
            code_lines = []

    def flush_quote():
        nonlocal quote_lines
        if quote_lines:
            text = " ".join(quote_lines)
            html.append(f"<blockquote>{_inline(text)}</blockquote>")
            quote_lines = []

    for raw in lines:
        line = raw.rstrip()

        if line.startswith("```"):
            flush_paragraph()
            flush_list()
            flush_quote()
            if in_code:
                flush_code()
            else:
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(raw)
            continue

        heading_match = re.match(r"^(#{1,3}) (.+)$", line)
        if heading_match:
            flush_paragraph()
            flush_list()
            flush_quote()
            level = min(len(heading_match.group(1)), 3)
            title = heading_match.group(2).strip()
            html.append(f'<h{level} id="{_slugify(title)}">{_inline(title)}</h{level}>')
            continue

        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_quote()
            continue

        if line.startswith("> "):
            flush_paragraph()
            flush_list()
            quote_lines.append(line[2:].strip())
            continue

        unordered = re.match(r"^- (.+)$", line)
        ordered = re.match(r"^\d+\. (.+)$", line)
        if unordered or ordered:
            flush_paragraph()
            flush_quote()
            next_type = "ol" if ordered else "ul"
            value = (ordered or unordered).group(1).strip()
            if list_type and list_type != next_type:
                flush_list()
            list_type = next_type
            list_items.append(value)
            continue

        paragraph.append(line.strip())

    flush_paragraph()
    flush_list()
    flush_quote()
    flush_code()
    return "\n".join(html)


def _inline(text: str) -> str:
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" target="_blank" rel="noreferrer">\1</a>',
        text,
    )
    return text
