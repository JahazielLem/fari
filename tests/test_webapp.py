from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from webapp.app import create_app
from webapp.meta import FARI_GENERATED_WITH
from webapp import wiki as wiki_module
from webapp.db import db


class FariWebAppTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test",
                "DATABASE": str(root / "fari.sqlite3"),
                "UPLOAD_DIR": str(root / "evidence"),
                "ATTACK_FLOW_DIR": str(root / "attack_flows"),
                "SBOM_DIR": str(root / "sbom"),
            }
        )
        self.client = self.app.test_client()
        self.login()
        self.create_assessment_and_investigation()

    def tearDown(self):
        self.temp.cleanup()

    def create_assessment_and_investigation(self):
        response = self.client.post(
            "/assessments/new",
            data={
                "client_name": "Example Aerospace",
                "title": "SpaceCAN Assessment",
                "mission_context": "Representative spacecraft bus lab.",
                "scope": "SpaceCAN monitor and local bus.",
                "authorization": "Authorized lab only.",
                "exclusions": "Physical and on-orbit behavior.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ASM-2026-0001", response.data)
        self.client.post(
            "/assessments/1/assets",
            data={
                "name": "SpaceCAN Monitor",
                "description": "Lab bus monitor.",
                "segment": "space",
                "access_model": "private",
                "coverage": "tested",
            },
            follow_redirects=True,
        )
        self.client.post(
            "/assessments/1/investigations/new",
            data={
                "asset_id": "1",
                "title": "Reply spoofing",
                "claim_description": "The monitor distinguishes forged reply-like frames.",
                "technical_reporter": "External Auditor",
                "method": "Dynamic bus injection",
                "environment": "Local lab",
                "scope_boundary": "Lab monitor only.",
                "gating": "on",
            },
            follow_redirects=True,
        )

    def login(self, client=None):
        client = client or self.client
        response = client.post(
            "/login",
            data={"username": "fari", "password": "toor"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Assessment workspace", response.data)
        return response

    def completed_investigation_data(self):
        return {
            "asset_id": "1",
            "title": "Reply spoofing",
            "claim_description": "The monitor distinguishes forged reply-like frames.",
            "technical_reporter": "External Auditor",
            "method": "Dynamic bus injection",
            "environment": "Local lab",
            "facts": "Injected frame was sent.\nDisplayed value changed.",
            "assertions": "The frame represents node 0x04.",
            "inferences": "Displayed state can be influenced by injected traffic.",
            "assumptions": "Monitor values may inform operators.",
            "contradictions": "",
            "gaps": "Physical response is not assessed.",
            "technical_sufficiency": "sufficient",
            "reachability_sufficiency": "partial",
            "mission_sufficiency": "partial",
            "conclusion": "does_not_meet",
            "scenario_state": "plausible",
            "confidence": "medium",
            "required_action": "remediate",
            "priority": "immediate",
            "scope_boundary": "Lab monitor only.",
            "rationale": "Forged traffic changes displayed state.",
            "recommendations": "Validate origin and freshness.",
            "acceptance_criteria": "Forged frames are rejected.",
            "status": "ready",
            "gating": "on",
        }

    def test_index_loads_existing_assessments_and_help_searches(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Assessment workspace", response.data)
        self.assertIn(b"SpaceCAN Assessment", response.data)
        self.assertIn(b"1 total assessments", response.data)
        self.assertIn(b"Apply filters", response.data)

        help_response = self.client.get("/help/search?q=sparta")
        self.assertEqual(help_response.status_code, 200)
        self.assertIn(b"SPARTA", help_response.data)

        scope_help = self.client.get("/help/search?q=osint")
        self.assertEqual(scope_help.status_code, 200)
        self.assertIn(b"Access basis", scope_help.data)
        self.assertIn(b"OSINT", scope_help.data)

        default_help = self.client.get("/help/search")
        self.assertEqual(default_help.status_code, 200)
        self.assertIn(b"Mission context", default_help.data)

        wiki_response = self.client.get("/wiki")
        self.assertEqual(wiki_response.status_code, 200)
        self.assertIn(b"FARI specification", wiki_response.data)
        self.assertIn(b"Simple worked example", wiki_response.data)

        traceability_response = self.client.get("/assessments/1/traceability")
        self.assertEqual(traceability_response.status_code, 200)
        self.assertIn(b"Assessment versions", traceability_response.data)

    def test_login_required_and_resources_page_available(self):
        anonymous = self.app.test_client()
        response = anonymous.get("/", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Access the workspace", response.data)
        self.assertIn(b"Open workspace", response.data)

        resources = self.client.get("/resources")
        self.assertEqual(resources.status_code, 200)
        self.assertIn(b"Reference material and downloadables", resources.data)
        self.assertIn(b"Manual fill template", resources.data)
        self.assertIn(b"Assessment JSON schema", resources.data)
        self.assertIn(b"SPD-5 companion profile", resources.data)

        download = self.client.get("/resources/download/spd5-companion")
        self.assertEqual(download.status_code, 200)
        self.assertIn(b"SPD-5", download.data)

    def test_database_uri_can_be_configured(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database_url = "sqlite:///" + str(root / "external.sqlite3")
            app = create_app(
                {
                    "TESTING": True,
                    "SECRET_KEY": "test",
                    "DATABASE": str(root / "fallback.sqlite3"),
                    "SQLALCHEMY_DATABASE_URI": database_url,
                    "UPLOAD_DIR": str(root / "evidence"),
                    "ATTACK_FLOW_DIR": str(root / "attack_flows"),
                    "SBOM_DIR": str(root / "sbom"),
                }
            )
            self.assertEqual(app.config["SQLALCHEMY_DATABASE_URI"], database_url)
            self.assertTrue((root / "external.sqlite3").exists())
            self.assertFalse((root / "fallback.sqlite3").exists())
            with app.app_context():
                db.session.remove()
                db.engine.dispose()

    def test_wiki_fallback_renders_when_spec_source_is_missing(self):
        missing = Path(self.temp.name) / "missing-spec.md"
        with patch.object(wiki_module, "SPEC_PATHS", [missing]):
            wiki_module.resolve_specification_path.cache_clear()
            wiki_module.load_specification_markdown.cache_clear()
            wiki_module.load_specification_outline.cache_clear()
            wiki_module.load_specification_html.cache_clear()
            response = self.client.get("/wiki")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"canonical FARI specification is not available", response.data)
            self.assertIn(b"versioned specification sources", response.data)

        wiki_module.resolve_specification_path.cache_clear()
        wiki_module.load_specification_markdown.cache_clear()
        wiki_module.load_specification_outline.cache_clear()
        wiki_module.load_specification_html.cache_clear()

    def test_spd5_companion_profile_can_be_initialized_and_exported(self):
        response = self.client.get("/assessments/1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SPD-5 companion checklist", response.data)
        self.assertIn(b"Set up companion profile", response.data)

        response = self.client.post(
            "/assessments/1/compliance/spd5-companion/create",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SPD-5 companion profile created", response.data)
        self.assertIn(b"Compliance scenario", response.data)
        self.assertIn(b"Governance", response.data)
        self.assertIn(b"SPD5-GOV-01", response.data)

        response = self.client.post(
            "/assessments/1/compliance/spd5-companion",
            data={
                "scenario": "partial_alignment",
                "summary": "Ground controls are in progress while link protections are being validated.",
                "notes": "Use claim records as the evidence source of truth.",
                "status_1": "implemented",
                "evidence_refs_1": "INV-0001-001, EVD-0001-001",
                "notes_1": "Policy confirmed in supplied governance material.",
                "status_2": "partially_implemented",
                "evidence_refs_2": "INV-0001-001",
                "notes_2": "Threat analysis exists but needs broader mission coverage.",
                "status_3": "planned",
                "evidence_refs_3": "AFB-0001-001",
                "notes_3": "SPARTA modeling has started.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SPD-5 companion checklist saved", response.data)
        self.assertIn(b"Partially Aligned", response.data)
        self.assertIn(b"Implemented", response.data)
        self.assertIn(b"Partially Implemented", response.data)

        exported = json.loads(self.client.get("/assessments/1/export.json").data)
        self.assertIn("compliance_profiles", exported)
        self.assertEqual(exported["compliance_profiles"][0]["scenario"], "partial_alignment")
        self.assertEqual(exported["compliance_profiles"][0]["posture"], "partially_aligned")
        self.assertEqual(exported["compliance_profiles"][0]["checks"][0]["control_id"], "SPD5-GOV-01")
        self.assertEqual(exported["compliance_profiles"][0]["checks"][0]["status"], "implemented")

    def test_complete_flow_closure_and_reports(self):
        response = self.client.post(
            "/investigations/1/edit",
            data=self.completed_investigation_data(),
            follow_redirects=True,
        )
        self.assertIn(b"Does Not Meet", response.data)
        self.assertIn(b"Scenario: Plausible", response.data)

        response = self.client.post(
            "/investigations/1/evidence",
            data={
                "description": "Injection output.",
                "file": (BytesIO(b"test evidence"), "evidence.txt"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertIn(b"EVD-0001-001", response.data)

        response = self.client.post(
            "/investigations/1/findings",
            data={
                "title": "Forged reply influences display",
                "state": "confirmed",
                "condition_text": "Reply-like traffic is displayed.",
                "observed_effect": "Displayed value changes.",
                "credible_impact": "Operators may see misleading state.",
                "sparta_id": "EX-0014.02",
                "sparta_name": "Bus Traffic Spoofing",
                "mapping_state": "confirmed",
                "mapping_rationale": "Forged internal bus traffic.",
                "include_sparta_countermeasures": "on",
            },
            follow_redirects=True,
        )
        self.assertIn(b"FND-0001-001", response.data)
        self.assertIn(b"Countermeasures in report", response.data)

        draft_report = self.client.get("/investigations/1/report.docx")
        self.assertEqual(draft_report.status_code, 200)
        with zipfile.ZipFile(BytesIO(draft_report.data)) as archive:
            document_xml = archive.read("word/document.xml")
            self.assertIn(b"DRAFT REPORT", document_xml)
            self.assertIn(b"SPARTA-Recommended Countermeasures", document_xml)
            self.assertIn(b"CM0031", document_xml)
            self.assertIn(b"Scenario Disposition", document_xml)
            self.assertIn(b"Plausible", document_xml)
            self.assertIn(FARI_GENERATED_WITH.encode(), document_xml)
        self.assertEqual(self.client.get("/investigations/1/report.pdf").status_code, 409)
        self.assertEqual(self.client.get("/assessments/1/consolidated.pdf").status_code, 409)

        response = self.client.post(
            "/investigations/1/status", data={"action": "close"}, follow_redirects=True
        )
        self.assertIn(b"Investigation closed", response.data)
        self.assertIn(b"Final and immutable", response.data)
        self.assertNotIn(b"Continue workflow", response.data)

        response = self.client.post(
            "/assessments/1/status", data={"action": "close"}, follow_redirects=True
        )
        self.assertIn(b"Assessment closed", response.data)

        investigation_report = self.client.get("/investigations/1/report.docx")
        self.assertEqual(investigation_report.status_code, 200)
        self.assertTrue(zipfile.is_zipfile(BytesIO(investigation_report.data)))
        with zipfile.ZipFile(BytesIO(investigation_report.data)) as archive:
            self.assertNotIn(b"DRAFT REPORT", archive.read("word/document.xml"))
            self.assertIn(b"FINAL", archive.read("word/document.xml"))
        investigation_pdf = self.client.get("/investigations/1/report.pdf")
        self.assertEqual(investigation_pdf.status_code, 200)
        self.assertTrue(investigation_pdf.data.startswith(b"%PDF-"))
        consolidated = self.client.get("/assessments/1/consolidated.docx")
        self.assertEqual(consolidated.status_code, 200)
        self.assertTrue(zipfile.is_zipfile(BytesIO(consolidated.data)))
        consolidated_pdf = self.client.get("/assessments/1/consolidated.pdf")
        self.assertEqual(consolidated_pdf.status_code, 200)
        self.assertTrue(consolidated_pdf.data.startswith(b"%PDF-"))

        output_dir = os.environ.get("FARI_TEST_OUTPUT_DIR")
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "web-investigation-report.docx").write_bytes(investigation_report.data)
            (output_path / "web-consolidated-report.docx").write_bytes(consolidated.data)

        exported = self.client.get("/assessments/1/export.json")
        self.assertIn(b'"overall_conclusion": "does_not_meet"', exported.data)
        self.assertIn(b'"status": "closed"', exported.data)
        self.assertIn(f'"generated_with": "{FARI_GENERATED_WITH}"'.encode(), exported.data)
        self.assertIn(b'"versions"', exported.data)

        locked = self.client.post(
            "/investigations/1/evidence",
            data={"file": (BytesIO(b"late"), "late.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(locked.status_code, 409)
        locked_edit = self.client.get("/investigations/1/edit", follow_redirects=True)
        self.assertIn(b"closed and immutable", locked_edit.data)
        self.assertEqual(self.client.post("/assessments/1/delete").status_code, 409)

    def test_invalid_normalization_preserves_submitted_fields(self):
        data = self.completed_investigation_data()
        data["facts"] = "FIELD MUST SURVIVE VALIDATION"
        data["rationale"] = ""
        response = self.client.post("/investigations/1/edit", data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Resolved conclusions require a rationale", response.data)
        self.assertIn(b"FIELD MUST SURVIVE VALIDATION", response.data)

        data = self.completed_investigation_data()
        data["conclusion"] = "meets"
        data["required_action"] = "remediate"
        response = self.client.post("/investigations/1/edit", data=data)
        self.assertIn(b"Meets cannot require Remediate", response.data)

    def test_delete_evidence_and_edit_sparta_finding(self):
        self.client.post(
            "/investigations/1/evidence",
            data={"description": "Temporary.", "file": (BytesIO(b"delete me"), "delete.txt")},
            content_type="multipart/form-data",
        )
        response = self.client.post("/evidence/1/delete", follow_redirects=True)
        self.assertIn(b"Evidence EVD-0001-001 deleted", response.data)
        self.assertNotIn(b"delete.txt", response.data)

        self.client.post(
            "/investigations/1/findings",
            data={
                "title": "Original finding",
                "state": "candidate",
                "mapping_state": "candidate",
            },
        )
        response = self.client.post(
            "/findings/1/edit",
            data={
                "title": "Updated finding",
                "state": "confirmed",
                "condition_text": "Updated condition",
                "observed_effect": "Updated effect",
                "credible_impact": "Updated impact",
                "sparta_id": "EX-0099",
                "sparta_name": "Updated SPARTA relationship",
                "mapping_state": "confirmed",
                "mapping_rationale": "Validated by reviewer.",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Updated finding", response.data)
        self.assertIn(b"EX-0099", response.data)

    def test_delete_asset_and_investigation_claim(self):
        self.client.post(
            "/investigations/1/evidence",
            data={"description": "Temporary.", "file": (BytesIO(b"delete me"), "delete.txt")},
            content_type="multipart/form-data",
        )
        evidence_dir = Path(self.temp.name) / "evidence" / "INV-0001-001"
        self.assertTrue(evidence_dir.exists())

        response = self.client.post("/assets/1/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Asset AST-0001-001 deleted", response.data)
        self.assertNotIn(b"SpaceCAN Monitor", response.data)

        detail = self.client.get("/investigations/1")
        self.assertIn(b"Not selected", detail.data)

        response = self.client.post("/investigations/1/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"claim CLM-0001-001 deleted", response.data)
        self.assertNotIn(b"Reply spoofing", response.data)
        self.assertFalse(evidence_dir.exists())

    def test_import_and_visualize_attack_flow_builder_file(self):
        bundle = {
            "type": "bundle",
            "id": "bundle--test",
            "objects": [
                {
                    "type": "attack-flow",
                    "id": "attack-flow--1",
                    "spec_version": "2.1",
                    "name": "SpaceCAN intrusion path",
                    "description": "Read-only test flow.",
                    "start_refs": ["attack-action--1"],
                },
                {
                    "type": "attack-action",
                    "id": "attack-action--1",
                    "spec_version": "2.1",
                    "name": "Inject forged frame",
                    "effect_refs": ["attack-condition--1"],
                    "external_references": [{"external_id": "T0001"}],
                },
                {
                    "type": "attack-condition",
                    "id": "attack-condition--1",
                    "spec_version": "2.1",
                    "name": "Display accepts frame",
                },
            ],
        }
        response = self.client.post(
            "/assessments/1/attack-flows",
            data={"file": (BytesIO(json.dumps(bundle).encode()), "spacecan.afb")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SpaceCAN intrusion path", response.data)
        self.assertIn(b"Inject forged frame", response.data)
        self.assertIn(b"Attack Flow diagram", response.data)

        native_builder = {
            "schema": "attack_flow_v2",
            "theme": "dark_theme",
            "layout": {
                "action-1": [100, -200],
                "action-2": [100, 100],
                "group-1": [500, -200],
            },
            "objects": [
                {
                    "id": "flow",
                    "instance": "flow-1",
                    "properties": [
                        ["name", "SPARTA Builder Flow"],
                        ["description", "Native Attack Flow Builder document."],
                    ],
                    "objects": ["line-1"],
                },
                {
                    "id": "action",
                    "instance": "action-1",
                    "properties": [
                        ["name", "REC-0001.01 Software Design"],
                        ["description", "Collect design information."],
                        ["ttp", [["tactic", "ST0001"], ["technique", "REC-0001"], ["subtechnique", "REC-0001.01"]]],
                    ],
                    "anchors": {"180": "anchor-1"},
                },
                {
                    "id": "action",
                    "instance": "action-2",
                    "properties": [
                        ["name", "Ungrouped validation action"],
                        ["description", "This action has no Group connection."],
                        ["ttp", [["technique", "EX-0014"]]],
                    ],
                    "anchors": {},
                },
                {"id": "horizontal_anchor", "instance": "anchor-1", "latches": ["latch-1"]},
                {"id": "generic_latch", "instance": "latch-1"},
                {
                    "id": "grouping",
                    "instance": "group-1",
                    "properties": [["name", "Gather Design Information"], ["description", "Group related actions."]],
                    "anchors": {"0": "anchor-2"},
                },
                {"id": "horizontal_anchor", "instance": "anchor-2", "latches": ["latch-2"]},
                {"id": "generic_latch", "instance": "latch-2"},
                {
                    "id": "dynamic_line",
                    "instance": "line-1",
                    "source": "latch-1",
                    "target": "latch-2",
                    "handles": [],
                },
            ],
        }
        response = self.client.post(
            "/assessments/1/attack-flows",
            data={"file": (BytesIO(json.dumps(native_builder).encode()), "sparta-native.afb")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SPARTA Builder Flow", response.data)
        self.assertIn(b"Attack Flow Builder v2", response.data)
        self.assertIn(b"REC-0001.01", response.data)
        self.assertIn(b"Drag the canvas to move", response.data)
        self.assertIn(b"Action groups", response.data)
        self.assertIn(b"Gather Design Information", response.data)
        self.assertIn(b"1 action</span>", response.data)
        self.assertIn(b"Ungrouped actions", response.data)
        self.assertIn(b"Ungrouped validation action", response.data)

        response = self.client.post("/attack-flows/1/delete", follow_redirects=True)
        self.assertIn(b"Attack Flow AFB-0001-001 deleted", response.data)
        self.assertNotIn(b"SpaceCAN intrusion path", response.data)

    def test_sparta_catalog_autocomplete_and_countermeasures(self):
        response = self.client.get("/sparta/ttps?q=bus%20traffic%20spoofing")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["version"], "v3.2")
        self.assertEqual(payload["items"][0]["id"], "EX-0014.02")
        self.assertEqual(payload["items"][0]["countermeasure_count"], 6)

        response = self.client.get("/sparta/ttps/EX-0014.02/countermeasures")
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.get_json()["items"]}
        self.assertIn("CM0031", ids)

    def test_guided_timeline_and_delete_open_assessment(self):
        response = self.client.get("/assessments/1")
        self.assertIn(b"Assessment workflow", response.data)
        self.assertIn(b"Scenario: Not Evaluated", response.data)
        self.assertIn(b"Delete assessment", response.data)

        response = self.client.get("/assessments/new")
        self.assertIn(b"Assessment workflow", response.data)
        self.assertIn(b"Current", response.data)
        self.assertIn(b"Pending", response.data)

        response = self.client.post("/assessments/1/delete", follow_redirects=True)
        self.assertIn(b"Assessment ASM-2026-0001", response.data)
        self.assertNotIn(b"SpaceCAN Assessment", response.data)
        self.assertEqual(self.client.get("/assessments/1").status_code, 404)

    def test_index_filters_status_and_result(self):
        self.client.post(
            "/investigations/1/edit",
            data=self.completed_investigation_data(),
            follow_redirects=True,
        )
        self.client.post(
            "/investigations/1/status", data={"action": "close"}, follow_redirects=True
        )
        self.client.post(
            "/assessments/1/status", data={"action": "close"}, follow_redirects=True
        )

        response = self.client.get("/?status=closed&result=does_not_meet&limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Showing 1 of 1 filtered assessments", response.data)
        self.assertIn(b"Does Not Meet", response.data)
        self.assertIn(b"PDF", response.data)

    def test_traceability_captures_versions_and_differences(self):
        response = self.client.post(
            "/assessments/1/versions/capture",
            data={"summary": "Initial framing snapshot."},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Revision v1 captured", response.data)
        self.assertIn(b"Initial framing snapshot.", response.data)

        self.client.post(
            "/investigations/1/edit",
            data=self.completed_investigation_data(),
            follow_redirects=True,
        )
        response = self.client.get("/assessments/1/traceability")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Current working state", response.data)
        self.assertIn(b"What changed", response.data)
        self.assertIn(b"Investigations", response.data)
        self.assertIn(b"Does Not Meet", response.data)

    def test_sbom_inventory_tracks_component_timeline(self):
        response = self.client.post(
            "/assessments/1/sbom",
            data={
                "file": (BytesIO(b"libfoo==1.4.2\nrequests==2.31.0\n"), "requirements.txt"),
                "asset_id": "1",
                "notes": "Baseline software inventory.",
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SBOM SBM-0001-001 ingested", response.data)
        self.assertIn(b"libfoo", response.data)
        self.assertIn(b"requests", response.data)

        response = self.client.post(
            "/inventory/components/1/events",
            data={
                "event_type": "vulnerability_detected",
                "occurred_at": "2026-06-08T12:00:00+00:00",
                "from_version": "1.4.2",
                "vulnerability_id": "CVE-2026-0001",
                "severity": "high",
                "status_after": "vulnerable",
                "summary": "libfoo 1.4.2 matches a known vulnerable release.",
                "component_notes": "Watching vendor remediation.",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Inventory event SBE-0001-002 recorded", response.data)
        self.assertIn(b"CVE-2026-0001", response.data)
        self.assertIn(b"Vulnerable", response.data)

        response = self.client.post(
            "/inventory/components/1/events",
            data={
                "event_type": "fix_verified",
                "occurred_at": "2026-06-10T12:00:00+00:00",
                "from_version": "1.4.2",
                "to_version": "1.4.5",
                "status_after": "fixed",
                "summary": "Updated libfoo to 1.4.5 and verified the fix.",
                "component_notes": "Closed after retest.",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Inventory event SBE-0001-003 recorded", response.data)
        self.assertIn(b"1.4.2", response.data)
        self.assertIn(b"1.4.5", response.data)
        self.assertIn(b"Fixed", response.data)

        exported = self.client.get("/assessments/1/export.json")
        self.assertIn(b'"sbom_documents"', exported.data)
        self.assertIn(b'"inventory_components"', exported.data)
        self.assertIn(b'"current_version": "1.4.5"', exported.data)
        self.assertIn(b'"status": "fixed"', exported.data)

    def test_cloud_and_other_segment_support_new_access_values(self):
        response = self.client.post(
            "/assessments/1/assets",
            data={
                "name": "Cloud Control Plane",
                "description": "Hosted telemetry API.",
                "segment": "cloud",
                "access_model": "private",
                "coverage": "reviewed",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cloud Control Plane", response.data)
        self.assertIn(b"Cloud", response.data)

        response = self.client.post(
            "/assessments/1/assets",
            data={
                "name": "Hybrid Research Surface",
                "description": "Exposure built from public material and third-party references.",
                "segment": "other",
                "access_model": "public",
                "coverage": "inferred",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Hybrid Research Surface", response.data)
        self.assertIn(b"Other", response.data)
        self.assertIn(b"Public", response.data)

        exported = self.client.get("/assessments/1/export.json")
        self.assertIn(b'"segment": "cloud"', exported.data)
        self.assertIn(b'"segment": "other"', exported.data)
        self.assertIn(b'"access_model": "public"', exported.data)


if __name__ == "__main__":
    unittest.main()
