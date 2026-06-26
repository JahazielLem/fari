#!/usr/bin/env python3
"""Generate the versioned FARI release PDFs from canonical Markdown sources."""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import build_release_docx
from tools.build_reference_docx import (
    BLUE,
    CALLOUT,
    DARK_BLUE,
    INK,
    LIGHT_BLUE,
    LIGHT_GRAY,
    MUTED,
    RESULT_STYLES,
    WHITE,
)
from webapp.meta import FARI_GENERATED_WITH, FARI_VERSION


ROOT = Path(__file__).resolve().parents[1]
VERSION_TAG = f"v{FARI_VERSION}"
SPEC_ROOT = ROOT / "spec"
RELEASE_ROOT = SPEC_ROOT / "releases" / VERSION_TAG
SOURCE_ROOT = RELEASE_ROOT / "_sources"
SPEC_DIR = RELEASE_ROOT / "specification"
REPORTS_DIR = RELEASE_ROOT / "reports"
TEMPLATE_DIR = RELEASE_ROOT / "manual-template"

CONTENT_WIDTH = 6.5 * inch


def hex_color(value: str):
    return colors.HexColor(f"#{value}")


def styles():
    sheet = getSampleStyleSheet()

    def add(name: str, parent: str, **kwargs) -> None:
        if name not in sheet:
            sheet.add(ParagraphStyle(name=name, parent=sheet[parent], **kwargs))

    add(
        "FariCoverBrand",
        "Title",
        fontName="Helvetica-Bold",
        fontSize=32,
        leading=38,
        textColor=hex_color(INK),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    add(
        "FariCoverLabel",
        "Title",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=hex_color(BLUE),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    add(
        "FariCoverTitle",
        "Title",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=hex_color(INK),
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    add(
        "FariCoverSubtitle",
        "BodyText",
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=hex_color(MUTED),
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    add(
        "FariCoverMeta",
        "BodyText",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=hex_color(MUTED),
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    add(
        "FariHeading1",
        "Heading1",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=hex_color(BLUE),
        spaceBefore=18,
        spaceAfter=10,
        keepWithNext=True,
    )
    add(
        "FariHeading2",
        "Heading2",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=hex_color(BLUE),
        spaceBefore=14,
        spaceAfter=7,
        keepWithNext=True,
    )
    add(
        "FariHeading3",
        "Heading3",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=hex_color(DARK_BLUE),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    )
    add(
        "FariBody",
        "BodyText",
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=hex_color(INK),
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    add(
        "FariBullet",
        "BodyText",
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        leftIndent=18,
        firstLineIndent=0,
        bulletIndent=6,
        textColor=hex_color(INK),
        spaceAfter=4,
    )
    add(
        "FariNumber",
        "FariBullet",
        leftIndent=20,
        bulletIndent=4,
    )
    add(
        "FariSmall",
        "BodyText",
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=hex_color(MUTED),
        spaceAfter=4,
    )
    add(
        "FariMono",
        "Code",
        fontName="Courier",
        fontSize=8.5,
        leading=10.5,
        textColor=hex_color(INK),
        backColor=hex_color(LIGHT_GRAY),
        borderPadding=6,
        borderWidth=0.5,
        borderColor=colors.HexColor("#CCD0DA"),
        spaceAfter=8,
    )
    add(
        "FariCallout",
        "BodyText",
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=hex_color(INK),
        spaceAfter=0,
    )
    return sheet


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def markdown_inline(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = text.replace("<br>", "\n").replace("<br/>", "\n")
    text = _escape(text)
    text = re.sub(
        r"`([^`]+)`",
        lambda match: f'<font name="Courier" color="#{DARK_BLUE}">{match.group(1)}</font>',
        text,
    )
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    return text.replace("\n", "<br/>")


def parse_table_line(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def result_style(text: str):
    normalized = re.sub(r"[*_`\[\]]", "", text).strip().lower()
    for key, style in RESULT_STYLES.items():
        if key in normalized:
            return style
    return RESULT_STYLES["not assessed"]


def release_notice_box(sheet):
    table = Table(
        [[
            Paragraph(
                "This is the versioned release edition of the FARI documentation bundle. "
                "Canonical working sources for this release are stored under the same version folder.",
                sheet["FariBody"],
            )
        ]],
        colWidths=[CONTENT_WIDTH],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), hex_color(CALLOUT)),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0, colors.white),
            ]
        )
    )
    return table


def result_banner(text: str, note: str):
    sheet = styles()
    label, fill, text_color = result_style(text)
    table = Table(
        [
            [Paragraph(f'<font color="#{text_color}"><b>{_escape(label)}</b></font>', sheet["FariCoverTitle"])],
            [Paragraph(f'<font color="#{text_color}">{_escape(note)}</font>', sheet["FariSmall"])],
        ],
        colWidths=[4.5 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), hex_color(fill)),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def cover_story(*, label: str, title: str, subtitle: str, version_string: str, show_result: str | None = None):
    sheet = styles()
    story = [
        Spacer(1, 2.1 * inch),
        Paragraph("FARI", sheet["FariCoverBrand"]),
        Paragraph(markdown_inline(label), sheet["FariCoverLabel"]),
        Paragraph(markdown_inline(title), sheet["FariCoverTitle"]),
        Paragraph(markdown_inline(subtitle), sheet["FariCoverSubtitle"]),
        Paragraph(
            markdown_inline(f"{version_string}  |  {date.today().isoformat()}"),
            sheet["FariCoverMeta"],
        ),
    ]
    if show_result:
        story.extend(
            [
                Spacer(1, 0.06 * inch),
                result_banner(show_result, "Qualitative executive conclusion from the example report"),
                Spacer(1, 0.2 * inch),
            ]
        )
    else:
        story.append(Spacer(1, 0.72 * inch))
    story.extend([release_notice_box(sheet), PageBreak()])
    return story


def callout_flowable(text: str):
    sheet = styles()
    table = Table(
        [[Paragraph(markdown_inline(text), sheet["FariCallout"])]],
        colWidths=[CONTENT_WIDTH],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), hex_color(CALLOUT)),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0, colors.white),
            ]
        )
    )
    return [table, Spacer(1, 0.08 * inch)]


def markdown_table_flowable(rows: list[list[str]]):
    sheet = styles()
    clean_rows: list[list[str]] = []
    max_cols = max(len(row) for row in rows)
    for row in rows:
        if all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in row):
            continue
        clean_rows.append(row + [""] * (max_cols - len(row)))
    if not clean_rows:
        return []

    paragraph_rows = [
        [Paragraph(markdown_inline(cell.strip() or " "), sheet["FariSmall"]) for cell in row]
        for row in clean_rows
    ]
    col_widths = [CONTENT_WIDTH / max_cols] * max_cols
    table = Table(paragraph_rows, colWidths=col_widths, repeatRows=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), hex_color(LIGHT_BLUE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), hex_color(INK)),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BCC0CC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for row_index, row in enumerate(clean_rows):
        label = row[0].strip().lower()
        if label in {"conclusion", "overall conclusion"} and len(row) > 1:
            _status_label, fill, text_color = result_style(row[1])
            commands.extend(
                [
                    ("BACKGROUND", (0, row_index), (-1, row_index), hex_color(fill)),
                    ("TEXTCOLOR", (0, row_index), (-1, row_index), hex_color(text_color)),
                    ("TOPPADDING", (0, row_index), (-1, row_index), 8),
                    ("BOTTOMPADDING", (0, row_index), (-1, row_index), 8),
                ]
            )
    table.setStyle(TableStyle(commands))
    return [table, Spacer(1, 0.1 * inch)]


def markdown_story(markdown_path: Path):
    sheet = styles()
    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    story = []
    idx = 0
    paragraph_lines: list[str] = []
    in_code = False
    code_language = ""
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            story.append(
                Paragraph(
                    markdown_inline(" ".join(line.strip() for line in paragraph_lines)),
                    sheet["FariBody"],
                )
            )
            paragraph_lines = []

    while idx < len(lines):
        line = lines[idx]

        if line.startswith("```"):
            flush_paragraph()
            if not in_code:
                in_code = True
                code_language = line[3:].strip()
                code_lines = []
            else:
                if code_language == "mermaid":
                    story.extend(
                        callout_flowable(
                            "Diagram source is available in the canonical Markdown edition."
                        )
                    )
                else:
                    story.append(Preformatted("\n".join(code_lines), sheet["FariMono"]))
                in_code = False
                code_language = ""
                code_lines = []
            idx += 1
            continue

        if in_code:
            code_lines.append(line)
            idx += 1
            continue

        if line.startswith("|") and idx + 1 < len(lines) and lines[idx + 1].startswith("|"):
            flush_paragraph()
            table_rows = []
            while idx < len(lines) and lines[idx].startswith("|"):
                table_rows.append(parse_table_line(lines[idx]))
                idx += 1
            story.extend(markdown_table_flowable(table_rows))
            continue

        if line.strip() == "<!-- pagebreak -->":
            flush_paragraph()
            story.append(PageBreak())
            idx += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            level = min(len(heading.group(1)), 3)
            text = heading.group(2)
            if level == 1 and (text.startswith("Framework for") or text.startswith("FARI ")):
                idx += 1
                continue
            story.append(
                Paragraph(
                    markdown_inline(text),
                    sheet[{1: "FariHeading1", 2: "FariHeading2", 3: "FariHeading3"}[level]],
                )
            )
            idx += 1
            continue

        bullet = re.match(r"^\s*-\s+(.+)$", line)
        numbered = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            item_text = bullet.group(1) if bullet else numbered.group(2)
            next_idx = idx + 1
            while (
                next_idx < len(lines)
                and re.match(r"^\s{2,}\S", lines[next_idx])
                and not re.match(r"^\s*[-*]\s+", lines[next_idx])
                and not re.match(r"^\s*\d+\.\s+", lines[next_idx])
            ):
                item_text += " " + lines[next_idx].strip()
                next_idx += 1
            if numbered:
                story.append(
                    Paragraph(
                        markdown_inline(item_text),
                        sheet["FariNumber"],
                        bulletText=f"{numbered.group(1)}.",
                    )
                )
            else:
                story.append(
                    Paragraph(
                        markdown_inline(item_text),
                        sheet["FariBullet"],
                        bulletText="•",
                    )
                )
            idx = next_idx
            continue

        if line.startswith(">"):
            flush_paragraph()
            quote_lines = []
            while idx < len(lines) and lines[idx].startswith(">"):
                quote_lines.append(lines[idx].lstrip("> "))
                idx += 1
            story.extend(callout_flowable(" ".join(quote_lines)))
            continue

        if line.strip() == "---":
            flush_paragraph()
            story.append(Spacer(1, 0.06 * inch))
            idx += 1
            continue

        if not line.strip():
            flush_paragraph()
        else:
            paragraph_lines.append(line)
        idx += 1

    flush_paragraph()
    return story


def cover_metadata(markdown_path: Path, title: str) -> dict:
    version_string = FARI_GENERATED_WITH
    if markdown_path.name == "FARI-SPECIFICATION-COMPLETE.md":
        return {
            "label": "Framework Specification",
            "title": f"Framework for Aerospace Research and Investigation {VERSION_TAG}",
            "subtitle": "Canonical specification, glossary, workflow, companion profile, and release guidance",
            "version_string": version_string,
            "show_result": None,
        }
    if markdown_path.name == "FARI-Manual-Template.md":
        return {
            "label": "Manual Fill Template",
            "title": f"FARI Manual Template {VERSION_TAG}",
            "subtitle": "Report-author worksheet aligned with the finalized workflow and field names",
            "version_string": version_string,
            "show_result": None,
        }
    for source, _pdf_target, label, report_title in build_release_docx.REPORT_BUILD_PLAN:
        if markdown_path == source:
            show_result = None
            try:
                show_result = build_release_docx._extract_conclusion(
                    source.read_text(encoding="utf-8")
                )
            except Exception:
                show_result = None
            return {
                "label": label,
                "title": report_title,
                "subtitle": f"Release source: {source.name}",
                "version_string": version_string,
                "show_result": show_result,
            }
    return {
        "label": title,
        "title": title,
        "subtitle": f"Generated with {version_string}",
        "version_string": version_string,
        "show_result": None,
    }


def pdf_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(hex_color(MUTED))
    canvas.drawString(
        0.65 * inch,
        0.38 * inch,
        f"Framework for Aerospace Research and Investigation | {FARI_GENERATED_WITH}",
    )
    canvas.drawRightString(7.85 * inch, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def cover_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(hex_color(MUTED))
    canvas.drawString(
        0.95 * inch,
        10.4 * inch,
        "FARI  |  Framework for Aerospace Research and Investigation",
    )
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(7.55 * inch, 0.52 * inch, f"Page {doc.page}")
    canvas.restoreState()


def render_pdf(markdown_path: Path, pdf_path: Path, title: str):
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    meta = cover_metadata(markdown_path, title)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.82 * inch,
        bottomMargin=0.72 * inch,
        title=title,
        author="Fari-Agent",
    )
    story = cover_story(**meta) + markdown_story(markdown_path)
    doc.build(story, onFirstPage=cover_footer, onLaterPages=pdf_footer)


def main():
    build_release_docx.main()
    spec_source = SOURCE_ROOT / "specification" / "FARI-SPECIFICATION-COMPLETE.md"
    template_source = SOURCE_ROOT / "templates" / "FARI-Manual-Template.md"
    render_pdf(
        spec_source,
        SPEC_DIR / f"FARI-Specification-{VERSION_TAG}.pdf",
        f"FARI Specification {VERSION_TAG}",
    )
    render_pdf(
        template_source,
        TEMPLATE_DIR / f"FARI-Manual-Template-{VERSION_TAG}.pdf",
        f"FARI Manual Template {VERSION_TAG}",
    )

    for source, pdf_target, _label, title in build_release_docx.REPORT_BUILD_PLAN:
        render_pdf(source, pdf_target, title)


if __name__ == "__main__":
    main()
