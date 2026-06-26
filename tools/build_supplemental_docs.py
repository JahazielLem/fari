#!/usr/bin/env python3
"""Build FARI walkthrough, datasheet, and optional technical form editions."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Inches, Pt

from build_reference_docx import (
    BLUE,
    INK,
    MUTED,
    add_callout,
    configure_running_furniture,
    configure_styles,
    markdown_to_doc,
    set_run_font,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC_CURRENT_ROOT = ROOT / "spec" / "current"

DOCUMENTS = [
    (
        SPEC_CURRENT_ROOT / "templates" / "FARI-Manual-Template.md",
        ROOT / "artifacts" / "templates" / "FARI-Manual-Template.docx",
        "Manual Fill Template",
        "FARI Manual Report Worksheet",
        "Framework-aligned fields for hand-filled assessments",
        [],
    ),
]


def add_cover(doc, label, title, subtitle):
    for _ in range(5):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    run = p.add_run("FARI")
    set_run_font(run, size=30, color=INK, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(label)
    set_run_font(run, size=18, color=BLUE, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(title)
    set_run_font(run, size=15, color=INK, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(subtitle)
    set_run_font(run, size=11, color=MUTED)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    run = p.add_run("Version 0.3 Draft  |  8 June 2026")
    set_run_font(run, size=10, color=MUTED, bold=True)

    for _ in range(3):
        doc.add_paragraph()

    add_callout(
        doc,
        "FARI preserves the auditor's technical independence while giving the "
        "Report Author a consistent path from source material to an executive "
        "conclusion.",
    )
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_evidence_appendix(doc, image_paths):
    if not image_paths:
        return
    doc.add_page_break()
    p = doc.add_paragraph(style="Heading 1")
    p.add_run("Evidence Visuals")
    add_callout(
        doc,
        "These figures reproduce supplied source material for the walkthrough. "
        "They do not expand the evidence boundary described in the analysis.",
    )
    for path in image_paths:
        p = doc.add_paragraph(style="Heading 2")
        p.add_run(path.stem.replace("_", " ").replace("-", " ").title())
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        picture = run.add_picture(str(path), width=Inches(5.9))
        alt_text = f"Supplied evidence screenshot: {path.stem.replace('_', ' ')}"
        picture._inline.docPr.set("descr", alt_text)
        picture._inline.docPr.set("title", alt_text)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"Supplied source material: {path.relative_to(ROOT)}")
        set_run_font(run, size=9, color=MUTED, italic=True)


def build_document(source, output, label, title, subtitle, image_paths):
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    configure_styles(doc)
    configure_running_furniture(doc.sections[0])
    add_cover(doc, label, title, subtitle)
    markdown_to_doc(doc, source, page_break=False)
    add_evidence_appendix(doc, image_paths)
    doc.core_properties.title = f"FARI {label}: {title}"
    doc.core_properties.subject = label
    doc.core_properties.author = "FARI Project"
    doc.core_properties.keywords = "FARI, space cybersecurity, reporting, SPARTA"
    doc.save(output)
    print(output)


def main():
    for args in DOCUMENTS:
        build_document(*args)


if __name__ == "__main__":
    main()
