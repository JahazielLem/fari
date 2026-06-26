"""Word report generation for web-created FARI assessments."""

from __future__ import annotations

from collections import Counter
from datetime import date
from html import escape
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from tools.build_reference_docx import (
    BLUE,
    INK,
    MUTED,
    add_callout,
    configure_running_furniture,
    configure_styles,
    set_cell_shading,
    set_repeat_table_header,
    set_run_font,
    set_table_geometry,
)
from webapp.meta import FARI_GENERATED_WITH
from webapp.sparta_parser import countermeasures_for


RESULT_STYLE = {
    "meets": ("MEETS", "84ABF8", "FFFFFF"),
    "does_not_meet": ("DOES NOT MEET", "B42318", "FFFFFF"),
    "inconclusive": ("INCONCLUSIVE", "B54708", "FFFFFF"),
    "not_assessed": ("NOT ASSESSED", "475467", "FFFFFF"),
}

LABELS = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "accept": "Accept",
    "remediate": "Remediate",
    "extend_investigation": "Extend Investigation",
    "retest": "Retest",
    "no_action": "No Action",
    "immediate": "Immediate",
    "planned": "Planned",
    "routine": "Routine",
    "none": "None",
    "sufficient": "Sufficient",
    "partial": "Partial",
    "insufficient": "Insufficient",
    "demonstrated": "Demonstrated",
    "plausible": "Plausible",
    "not_demonstrated": "Not Demonstrated",
    "not_evaluated": "Not Evaluated",
    "tracked": "Tracked",
    "vulnerable": "Vulnerable",
    "update_in_progress": "Update In Progress",
    "fixed": "Fixed",
    "accepted": "Accepted",
    "not_affected": "Not Affected",
    "manual_snapshot": "Manual Snapshot",
    "assessment_closed": "Assessment Closed",
    "live_state": "Live State",
    "not_verified": "Not Verified",
    "implemented": "Implemented",
    "partially_implemented": "Partially Implemented",
    "planned": "Planned",
    "not_implemented": "Not Implemented",
    "not_applicable": "Not Applicable",
    "aligned": "Aligned",
    "partially_aligned": "Partially Aligned",
    "gap_identified": "Gap Identified",
    "not_started": "Not Started",
    "evidence_backed_alignment": "Evidence-Backed Alignment",
    "partial_alignment": "Partial Alignment",
    "compensating_controls": "Compensating Controls",
    "inconclusive_scope_boundary": "Inconclusive Due To Scope",
    "supplier_attestation_pending": "Supplier Attestation Pending",
    "continuous_assurance": "Continuous Assurance",
    "direct": "Direct",
    "supporting": "Supporting",
}


def human(value: str) -> str:
    return LABELS.get(value, value.replace("_", " ").title())


def revision_label(assessment) -> str:
    try:
        count = assessment["revision_count"]
    except (KeyError, TypeError):
        count = getattr(assessment, "revision_count", 0)
    return f"v{count}" if count else "v0"


def add_cover(
    doc, label: str, title: str, client_name: str, report_author: str, document_state: str
):
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("FARI")
    set_run_font(run, size=31, color=INK, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(label)
    set_run_font(run, size=18, color=BLUE, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run(title)
    set_run_font(run, size=15, color=MUTED)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"Client: {client_name}  |  Report Author: {report_author}")
    set_run_font(run, size=10.5, color=MUTED, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(date.today().isoformat())
    set_run_font(run, size=10, color=MUTED)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"Generated with {FARI_GENERATED_WITH}")
    set_run_font(run, size=9.5, color=MUTED)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(document_state)
    set_run_font(
        run,
        size=16,
        color="B42318" if document_state == "DRAFT" else "15803D",
        bold=True,
    )
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_heading(doc, text: str, level: int = 1):
    p = doc.add_paragraph(style=f"Heading {min(level, 3)}")
    p.add_run(text)
    return p


def add_result_banner(doc, conclusion: str, confidence: str, action: str):
    label, fill, text_color = RESULT_STYLE.get(
        conclusion, RESULT_STYLE["not_assessed"]
    )
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [9360])
    set_repeat_table_header(table.rows[0])
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(label)
    set_run_font(run, size=20, color=text_color, bold=True)
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(
        f"Confidence: {human(confidence)}  |  Required Action: {human(action)}"
    )
    set_run_font(run, size=10.5, color=text_color, bold=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_key_value_table(doc, rows):
    table = doc.add_table(rows=1, cols=2)
    set_table_geometry(table, [2700, 6660])
    set_repeat_table_header(table.rows[0])
    table.cell(0, 0).text = "Field"
    table.cell(0, 1).text = "Result"
    for cell in table.rows[0].cells:
        set_cell_shading(cell, "E8EEF5")
        for run in cell.paragraphs[0].runs:
            set_run_font(run, size=9.5, color=INK, bold=True)
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = str(label)
        cells[1].text = str(value or "Not supplied")
        for run in cells[0].paragraphs[0].runs:
            set_run_font(run, size=9.2, color=INK, bold=True)
        for run in cells[1].paragraphs[0].runs:
            set_run_font(run, size=9.2, color=INK)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_list_section(doc, title: str, text: str, level: int = 2):
    add_heading(doc, title, level)
    items = [item.strip() for item in (text or "").splitlines() if item.strip()]
    if not items:
        p = doc.add_paragraph()
        run = p.add_run("Not supplied.")
        set_run_font(run, size=10.5, color=MUTED, italic=True)
        return
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item)


def add_findings(doc, findings):
    add_heading(doc, "Findings and SPARTA Relationships", 2)
    if not findings:
        add_callout(doc, "No normalized findings have been added.")
        return
    for finding in findings:
        add_heading(doc, f"{finding['fari_id']}: {finding['title']}", 3)
        add_key_value_table(
            doc,
            [
                ("State", human(finding["state"])),
                ("Condition", finding["condition_text"]),
                ("Observed Effect", finding["observed_effect"]),
                ("Credible Impact", finding["credible_impact"]),
                (
                    "SPARTA",
                    (
                        f"{finding['sparta_id']} {finding['sparta_name']}"
                        if finding["sparta_id"]
                        else "No mapping supplied"
                    ),
                ),
                ("Mapping State", human(finding["mapping_state"])),
                ("Mapping Rationale", finding["mapping_rationale"]),
            ],
        )
        if finding["include_sparta_countermeasures"] and finding["sparta_id"]:
            add_sparta_countermeasures(doc, finding["sparta_id"], 3)


def add_sparta_countermeasures(doc, sparta_id: str, level: int = 3):
    items = countermeasures_for(sparta_id)
    add_heading(doc, f"SPARTA-Recommended Countermeasures for {sparta_id}", level)
    if not items:
        add_callout(doc, "No linked countermeasures were found in the local SPARTA catalog.")
        return
    add_key_value_table(
        doc,
        [
            (f"{item['id']}: {item['name']}", item["description"] or "No description supplied.")
            for item in items
        ],
    )


def build_investigation_report(assessment, investigation, asset, evidence, findings):
    document_state = "FINAL" if investigation["status"] == "closed" else "DRAFT"
    doc = Document()
    configure_styles(doc)
    configure_running_furniture(doc.sections[0])
    add_cover(
        doc,
        "Investigation Report",
        investigation["title"],
        assessment["client_name"],
        assessment["report_author"],
        document_state,
    )
    if document_state == "DRAFT":
        add_callout(
            doc,
            "DRAFT REPORT: This document may change until the investigation is closed.",
        )
    add_result_banner(
        doc,
        investigation["conclusion"],
        investigation["confidence"],
        investigation["required_action"],
    )
    add_heading(doc, "1. FARI Result Card", 1)
    add_key_value_table(
        doc,
        [
            ("Conclusion", human(investigation["conclusion"])),
            ("Scenario Disposition", human(investigation["scenario_state"])),
            ("Confidence", human(investigation["confidence"])),
            ("Required Action", human(investigation["required_action"])),
            ("Generated With", FARI_GENERATED_WITH),
            ("Assessment Revision", revision_label(assessment)),
            ("Priority", human(investigation["priority"])),
            ("Scope Boundary", investigation["scope_boundary"]),
            ("Rationale", investigation["rationale"]),
        ],
    )
    add_heading(doc, "2. Frame", 1)
    add_key_value_table(
        doc,
        [
            ("Assessment", assessment["fari_id"]),
            ("Assessment Revision", revision_label(assessment)),
            ("Client", assessment["client_name"]),
            ("Investigation", investigation["fari_id"]),
            ("Claim", investigation["claim_id"]),
            ("Claim Description", investigation["claim_description"]),
            ("Gating Claim", "Yes" if investigation["gating"] else "No"),
            ("Asset", asset["fari_id"] + " - " + asset["name"] if asset else "Not supplied"),
            ("Technical Reporter", investigation["technical_reporter"]),
            ("Report Author", assessment["report_author"]),
            ("Method", investigation["method"]),
            ("Environment", investigation["environment"]),
        ],
    )
    add_heading(doc, "3. Acquire", 1)
    add_list_section(doc, "Evidence-Backed Facts", investigation["facts"])
    add_list_section(doc, "Evidence-Producer Assertions", investigation["assertions"])
    add_list_section(doc, "Report-Author Inferences", investigation["inferences"])
    add_list_section(doc, "Assumptions", investigation["assumptions"])
    add_list_section(doc, "Contradictions", investigation["contradictions"])
    add_list_section(doc, "Missing Information", investigation["gaps"])
    add_heading(doc, "Evidence Sufficiency", 2)
    add_key_value_table(
        doc,
        [
            ("Technical Condition", human(investigation["technical_sufficiency"])),
            ("Reachability", human(investigation["reachability_sufficiency"])),
            ("Mission Consequence", human(investigation["mission_sufficiency"])),
        ],
    )
    add_heading(doc, "Evidence Index", 2)
    if evidence:
        add_key_value_table(
            doc,
            [
                (
                    item["fari_id"],
                    f"<strong>{item['description']}</strong> | {item['filename']} <br>SHA-256 {item['sha256']}",
                )
                for item in evidence
            ],
        )
    else:
        add_callout(doc, "No evidence files have been uploaded.")
    add_heading(doc, "4. Relate", 1)
    add_findings(doc, findings)
    add_heading(doc, "5. Inform", 1)
    add_list_section(doc, "Recommendations", investigation["recommendations"])
    add_list_section(doc, "Acceptance Criteria", investigation["acceptance_criteria"])
    add_heading(doc, "Closing Result", 1)
    add_result_banner(
        doc,
        investigation["conclusion"],
        investigation["confidence"],
        investigation["required_action"],
    )
    doc.core_properties.author = assessment["report_author"]
    doc.core_properties.title = f"{investigation['fari_id']} {investigation['title']}"
    doc.core_properties.subject = FARI_GENERATED_WITH
    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output


def overall_conclusion(investigations) -> str:
    gating = [row for row in investigations if row["gating"]]
    if not gating:
        return "not_assessed"
    values = {row["conclusion"] for row in gating}
    if "does_not_meet" in values:
        return "does_not_meet"
    if "inconclusive" in values or "not_assessed" in values:
        return "inconclusive"
    return "meets"


def overall_confidence(investigations) -> str:
    values = {row["confidence"] for row in investigations}
    if "low" in values:
        return "low"
    if "medium" in values:
        return "medium"
    return "high" if values else "low"


def consolidated_action(conclusion: str) -> str:
    return {
        "meets": "accept",
        "does_not_meet": "remediate",
        "inconclusive": "extend_investigation",
        "not_assessed": "extend_investigation",
    }[conclusion]


def build_consolidated_report(assessment, assets, investigations):
    document_state = "FINAL" if assessment["status"] == "closed" else "DRAFT"
    conclusion = overall_conclusion(investigations)
    confidence = overall_confidence(investigations)
    action = consolidated_action(conclusion)
    doc = Document()
    configure_styles(doc)
    configure_running_furniture(doc.sections[0])
    add_cover(
        doc,
        "Consolidated Assessment Report",
        assessment["title"],
        assessment["client_name"],
        assessment["report_author"],
        document_state,
    )
    if document_state == "DRAFT":
        add_callout(
            doc,
            "DRAFT REPORT: This document may change until the assessment is closed.",
        )
    add_result_banner(doc, conclusion, confidence, action)
    add_heading(doc, "1. Overall FARI Result Card", 1)
    add_key_value_table(
        doc,
        [
            ("Overall Conclusion", human(conclusion)),
            ("Confidence", human(confidence)),
            ("Required Action", human(action)),
            ("Generated With", FARI_GENERATED_WITH),
            ("Assessment Revision", revision_label(assessment)),
            ("Assessment", assessment["fari_id"]),
            ("Client", assessment["client_name"]),
            ("Scope Boundary", assessment["scope"]),
            (
                "Rationale",
                "Derived from declared gating claims without averaging results.",
            ),
        ],
    )
    add_heading(doc, "2. Frame and Client Context", 1)
    add_key_value_table(
        doc,
        [
            ("Mission Context", assessment["mission_context"]),
            ("Scope", assessment["scope"]),
            ("Authorization", assessment["authorization"]),
            ("Exclusions", assessment["exclusions"]),
            ("Report Author", assessment["report_author"]),
        ],
    )
    add_heading(doc, "3. Asset Register", 1)
    add_key_value_table(
        doc,
        [
            (
                asset["fari_id"],
                f"{asset['name']} | {human(asset['segment'])} | "
                f"{human(asset['coverage'])} | {asset['description']}",
            )
            for asset in assets
        ]
        or [("Assets", "No assets registered")],
    )
    add_heading(doc, "4. Investigation Results", 1)
    for investigation in investigations:
        add_heading(
            doc,
            f"{investigation['fari_id']}: {investigation['title']}",
            2,
        )
        add_result_banner(
            doc,
            investigation["conclusion"],
            investigation["confidence"],
            investigation["required_action"],
        )
        add_key_value_table(
            doc,
            [
                ("Claim", f"{investigation['claim_id']}: {investigation['claim_description']}"),
                ("Gating", "Yes" if investigation["gating"] else "No"),
                ("Priority", human(investigation["priority"])),
                ("Scenario Disposition", human(investigation["scenario_state"])),
                ("Technical Sufficiency", human(investigation["technical_sufficiency"])),
                ("Reachability Sufficiency", human(investigation["reachability_sufficiency"])),
                ("Mission Sufficiency", human(investigation["mission_sufficiency"])),
                ("Rationale", investigation["rationale"]),
            ],
        )
        add_heading(doc, "Evidence Index", 3)
        if investigation.evidence:
            add_key_value_table(
                doc,
                [
                    (
                        item["fari_id"],
                        f"{item['filename']} | SHA-256 {item['sha256']} | {item['description']}",
                    )
                    for item in investigation.evidence
                ],
            )
        else:
            add_callout(doc, "No evidence files have been uploaded.")
        add_findings(doc, investigation.findings)
    add_heading(doc, "5. Totalized Results", 1)
    counts = Counter(row["conclusion"] for row in investigations)
    add_key_value_table(
        doc,
        [
            (RESULT_STYLE[key][0], counts.get(key, 0))
            for key in ("meets", "does_not_meet", "inconclusive", "not_assessed")
        ],
    )
    scenario_counts = Counter(row["scenario_state"] for row in investigations)
    add_heading(doc, "Scenario Dispositions", 2)
    add_key_value_table(
        doc,
        [
            (human(key), scenario_counts.get(key, 0))
            for key in ("demonstrated", "plausible", "not_demonstrated", "not_evaluated")
        ],
    )
    add_heading(doc, "6. Required Actions", 1)
    for investigation in investigations:
        add_heading(doc, investigation["fari_id"], 2)
        add_list_section(doc, "Recommendations", investigation["recommendations"], 3)
        add_list_section(doc, "Acceptance Criteria", investigation["acceptance_criteria"], 3)
    add_heading(doc, "Closing Overall Result", 1)
    add_result_banner(doc, conclusion, confidence, action)
    doc.core_properties.author = assessment["report_author"]
    doc.core_properties.title = f"{assessment['fari_id']} Consolidated Assessment"
    doc.core_properties.subject = FARI_GENERATED_WITH
    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output


def build_investigation_pdf(assessment, investigation, asset, evidence, findings):
    """Build the immutable final investigation report as a PDF."""
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="FariTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#4C4F69"),
            alignment=TA_CENTER,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FariHeading",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#1E66F5"),
            spaceBefore=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FariSmall",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#6C6F85"),
        )
    )

    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=f"{investigation['fari_id']} {investigation['title']}",
        author=assessment["report_author"],
    )
    story = [
        Spacer(1, 1.1 * inch),
        Paragraph("FARI<br/>FINAL INVESTIGATION<br/>REPORT", styles["FariHeading"]),
        Paragraph(escape(investigation["title"]), styles["FariTitle"]),
        Paragraph(
            f"Client: {escape(assessment['client_name'])}<br/>"
            f"Report Author: {escape(assessment['report_author'])}<br/>"
            f"Closed report generated: {date.today().isoformat()}<br/>"
            f"Generated with {escape(FARI_GENERATED_WITH)}",
            styles["BodyText"],
        ),
        Spacer(1, 0.3 * inch),
        _pdf_result_banner(investigation, styles),
        PageBreak(),
        Paragraph("FARI Result Card", styles["FariHeading"]),
        _pdf_key_value(
            [
                ("Conclusion", human(investigation["conclusion"])),
                ("Scenario Disposition", human(investigation["scenario_state"])),
                ("Confidence", human(investigation["confidence"])),
                ("Required Action", human(investigation["required_action"])),
                ("Generated With", FARI_GENERATED_WITH),
                ("Assessment Revision", revision_label(assessment)),
                ("Priority", human(investigation["priority"])),
                ("Scope Boundary", investigation["scope_boundary"]),
                ("Rationale", investigation["rationale"]),
            ],
            styles,
        ),
        Paragraph("Frame", styles["FariHeading"]),
        _pdf_key_value(
            [
                ("Assessment", assessment["fari_id"]),
                ("Assessment Revision", revision_label(assessment)),
                ("Investigation", investigation["fari_id"]),
                ("Claim", investigation["claim_id"]),
                ("Claim Description", investigation["claim_description"]),
                ("Asset", f"{asset['fari_id']} - {asset['name']}" if asset else "Not supplied"),
                ("Technical Reporter", investigation["technical_reporter"]),
                ("Method", investigation["method"]),
                ("Environment", investigation["environment"]),
            ],
            styles,
        ),
        Paragraph("Acquire", styles["FariHeading"]),
    ]
    for title, text in [
        ("Evidence-Backed Facts", investigation["facts"]),
        ("Evidence-Producer Assertions", investigation["assertions"]),
        ("Report-Author Inferences", investigation["inferences"]),
        ("Assumptions", investigation["assumptions"]),
        ("Contradictions", investigation["contradictions"]),
        ("Missing Information", investigation["gaps"]),
    ]:
        story.extend(_pdf_list(title, text, styles))
    story.extend(
        [
            Paragraph("Evidence Index", styles["FariHeading"]),
            _pdf_key_value(
                [
                    (
                        item["fari_id"],
                        f"{item['filename']} | SHA-256 {item['sha256']} | {item['description']}",
                    )
                    for item in evidence
                ]
                or [("Evidence", "No evidence files uploaded.")],
                styles,
            ),
            Paragraph("Relate: Findings and SPARTA", styles["FariHeading"]),
        ]
    )
    for finding in findings:
        story.append(Paragraph(f"{escape(finding['fari_id'])}: {escape(finding['title'])}", styles["Heading3"]))
        story.append(
            _pdf_key_value(
                [
                    ("State", human(finding["state"])),
                    ("Condition", finding["condition_text"]),
                    ("Observed Effect", finding["observed_effect"]),
                    ("Credible Impact", finding["credible_impact"]),
                    ("SPARTA", f"{finding['sparta_id']} {finding['sparta_name']}".strip() or "No mapping supplied"),
                    ("Mapping State", human(finding["mapping_state"])),
                    ("Mapping Rationale", finding["mapping_rationale"]),
                ],
                styles,
            )
        )
        if finding["include_sparta_countermeasures"] and finding["sparta_id"]:
            items = countermeasures_for(finding["sparta_id"])
            story.append(
                Paragraph(
                    f"SPARTA-Recommended Countermeasures for {escape(finding['sparta_id'])}",
                    styles["Heading3"],
                )
            )
            story.append(
                _pdf_key_value(
                    [
                        (f"{item['id']}: {item['name']}", item["description"])
                        for item in items
                    ]
                    or [("SPARTA", "No linked countermeasures were found in the local catalog.")],
                    styles,
                )
            )
    story.extend(
        [
            Paragraph("Inform", styles["FariHeading"]),
            *_pdf_list("Recommendations", investigation["recommendations"], styles),
            *_pdf_list("Acceptance Criteria", investigation["acceptance_criteria"], styles),
            Spacer(1, 0.2 * inch),
            _pdf_result_banner(investigation, styles),
        ]
    )
    doc.build(story, onFirstPage=_pdf_footer, onLaterPages=_pdf_footer)
    output.seek(0)
    return output


def build_consolidated_pdf(assessment, assets, investigations):
    """Build the immutable final assessment-level report as a PDF."""
    output = BytesIO()
    styles = _pdf_styles()
    conclusion = overall_conclusion(investigations)
    confidence = overall_confidence(investigations)
    action = consolidated_action(conclusion)
    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=f"{assessment['fari_id']} Consolidated Assessment",
        author=assessment["report_author"],
    )
    overall = {
        "conclusion": conclusion,
        "confidence": confidence,
        "required_action": action,
    }
    story = [
        Paragraph("FARI<br/>FINAL CONSOLIDATED<br/>ASSESSMENT", styles["FariHeading"]),
        Spacer(1, 1.1 * inch),
        Paragraph(escape(assessment["title"]), styles["FariTitle"]),
        Paragraph(
            f"Client: {escape(assessment['client_name'])}<br/>"
            f"Report Author: {escape(assessment['report_author'])}<br/>"
            f"Final report generated: {date.today().isoformat()}<br/>"
            f"Generated with {escape(FARI_GENERATED_WITH)}",
            styles["BodyText"],
        ),
        Spacer(1, 0.3 * inch),
        _pdf_result_banner(overall, styles),
        PageBreak(),
        Paragraph("Overall FARI Result Card", styles["FariHeading"]),
        _pdf_key_value(
            [
                ("Overall Conclusion", human(conclusion)),
                ("Confidence", human(confidence)),
                ("Required Action", human(action)),
                ("Generated With", FARI_GENERATED_WITH),
                ("Assessment Revision", revision_label(assessment)),
                ("Assessment", assessment["fari_id"]),
                ("Scope Boundary", assessment["scope"]),
                ("Derivation", "Derived from declared gating claims without averaging."),
            ],
            styles,
        ),
        Paragraph("Frame and Client Context", styles["FariHeading"]),
        _pdf_key_value(
            [
                ("Mission Context", assessment["mission_context"]),
                ("Scope", assessment["scope"]),
                ("Authorization", assessment["authorization"]),
                ("Exclusions", assessment["exclusions"]),
            ],
            styles,
        ),
        Paragraph("Asset Register", styles["FariHeading"]),
        _pdf_key_value(
            [
                (
                    asset["fari_id"],
                    f"{asset['name']} | {human(asset['segment'])} | "
                    f"{human(asset['coverage'])} | {asset['description']}",
                )
                for asset in assets
            ]
            or [("Assets", "No assets registered.")],
            styles,
        ),
        PageBreak(),
        Paragraph("Investigation Results", styles["FariHeading"]),
    ]
    for investigation in investigations:
        story.extend(
            [
                Paragraph(
                    f"{escape(investigation['fari_id'])}: {escape(investigation['title'])}",
                    styles["Heading2"],
                ),
                _pdf_result_banner(investigation, styles),
                _pdf_key_value(
                    [
                        ("Claim", f"{investigation['claim_id']}: {investigation['claim_description']}"),
                        ("Gating", "Yes" if investigation["gating"] else "No"),
                        ("Scenario Disposition", human(investigation["scenario_state"])),
                        ("Technical Sufficiency", human(investigation["technical_sufficiency"])),
                        ("Reachability Sufficiency", human(investigation["reachability_sufficiency"])),
                        ("Mission Sufficiency", human(investigation["mission_sufficiency"])),
                        ("Scope Boundary", investigation["scope_boundary"]),
                        ("Rationale", investigation["rationale"]),
                    ],
                    styles,
                ),
                Paragraph("Evidence Index", styles["Heading3"]),
                _pdf_key_value(
                    [
                        (
                            item["fari_id"],
                            f"{item['filename']} | SHA-256 {item['sha256']} | {item['description']}",
                        )
                        for item in investigation.evidence
                    ]
                    or [("Evidence", "No evidence files uploaded.")],
                    styles,
                ),
                Paragraph("Findings and SPARTA", styles["Heading3"]),
            ]
        )
        for finding in investigation.findings:
            story.append(
                _pdf_key_value(
                    [
                        ("Finding", f"{finding['fari_id']}: {finding['title']}"),
                        ("State", human(finding["state"])),
                        ("Condition", finding["condition_text"]),
                        ("Observed Effect", finding["observed_effect"]),
                        ("Credible Impact", finding["credible_impact"]),
                        ("SPARTA", f"{finding['sparta_id']} {finding['sparta_name']}".strip() or "No mapping supplied"),
                    ],
                    styles,
                )
            )
            if finding["include_sparta_countermeasures"] and finding["sparta_id"]:
                story.append(
                    Paragraph(
                        f"SPARTA-Recommended Countermeasures for {escape(finding['sparta_id'])}",
                        styles["Heading3"],
                    )
                )
                story.append(
                    _pdf_key_value(
                        [
                            (f"{item['id']}: {item['name']}", item["description"])
                            for item in countermeasures_for(finding["sparta_id"])
                        ]
                        or [("SPARTA", "No linked countermeasures were found in the local catalog.")],
                        styles,
                    )
                )
        if not investigation.findings:
            story.append(Paragraph("No normalized findings.", styles["FariSmall"]))
        story.extend(
            [
                *_pdf_list("Recommendations", investigation["recommendations"], styles),
                *_pdf_list("Acceptance Criteria", investigation["acceptance_criteria"], styles),
                Spacer(1, 0.15 * inch),
            ]
        )

    conclusion_counts = Counter(row["conclusion"] for row in investigations)
    scenario_counts = Counter(row["scenario_state"] for row in investigations)
    story.extend(
        [
            PageBreak(),
            Paragraph("Totalized Results", styles["FariHeading"]),
            _pdf_key_value(
                [
                    (RESULT_STYLE[key][0], conclusion_counts.get(key, 0))
                    for key in ("meets", "does_not_meet", "inconclusive", "not_assessed")
                ],
                styles,
            ),
            Paragraph("Scenario Dispositions", styles["FariHeading"]),
            _pdf_key_value(
                [
                    (human(key), scenario_counts.get(key, 0))
                    for key in ("demonstrated", "plausible", "not_demonstrated", "not_evaluated")
                ],
                styles,
            ),
            Paragraph("Closing Overall Result", styles["FariHeading"]),
            _pdf_result_banner(overall, styles),
        ]
    )
    doc.build(story, onFirstPage=_pdf_footer, onLaterPages=_pdf_footer)
    output.seek(0)
    return output


def _pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="FariTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#4C4F69"),
            alignment=TA_CENTER,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FariHeading",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#1E66F5"),
            alignment=TA_CENTER,
            spaceBefore=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FariSmall",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#6C6F85"),
        )
    )
    return styles


def _pdf_result_banner(investigation, styles):
    label, fill, _text_color = RESULT_STYLE.get(
        investigation["conclusion"], RESULT_STYLE["not_assessed"]
    )
    table = Table(
        [
            [Paragraph(f"<b>{label}</b>", styles["Title"])],
            [
                Paragraph(
                    f"Confidence: {human(investigation['confidence'])} | "
                    f"Required Action: {human(investigation['required_action'])}",
                    styles["BodyText"],
                )
            ],
        ],
        colWidths=[7.1 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(f"#{fill}")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _pdf_key_value(rows, styles):
    data = [
        [
            Paragraph("<b>Field</b>", styles["BodyText"]),
            Paragraph("<b>Result</b>", styles["BodyText"]),
        ]
    ]
    for label, value in rows:
        data.append(
            [
                Paragraph(f"<b>{escape(str(label))}</b>", styles["BodyText"]),
                Paragraph(escape(str(value or "Not supplied")).replace("\n", "<br/>"), styles["BodyText"]),
            ]
        )
    table = Table(data, colWidths=[1.6 * inch, 5.5 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E9EF")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BCC0CC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _pdf_list(title, text, styles):
    items = [item.strip() for item in (text or "").splitlines() if item.strip()]
    result = [Paragraph(escape(title), styles["Heading3"])]
    if not items:
        result.append(Paragraph("Not supplied.", styles["FariSmall"]))
    else:
        result.extend(
            Paragraph(f"• {escape(item)}", styles["BodyText"]) for item in items
        )
    return result


def _pdf_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6C6F85"))
    canvas.drawString(
        0.65 * inch,
        0.38 * inch,
        f"Framework for Aerospace Research and Investigation FINAL REPORT | {FARI_GENERATED_WITH}",
    )
    canvas.drawRightString(7.85 * inch, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()
