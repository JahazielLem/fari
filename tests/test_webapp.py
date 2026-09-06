from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from webapp.app import create_app
from webapp.db import Assessment, AssetSource, Investigation, db
from webapp.meta import FARI_GENERATED_WITH, FARI_VERSION
from webapp.asset_sources import parse_asset_source


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
                "ASSET_SOURCE_DIR": str(root / "sources"),
            }
        )
        self.client = self.app.test_client()
        self.login()
        self.create_assessment_and_investigation()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp.cleanup()

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
                "title": "Reply validation",
                "claim_description": "The monitor distinguishes forged reply-like frames.",
                "technical_reporter": "External Auditor",
                "method": "Dynamic bus validation",
                "environment": "Local lab",
                "scope_boundary": "Lab monitor only.",
                "gating": "on",
            },
            follow_redirects=True,
        )

    def completed_investigation_data(self):
        return {
            "asset_id": "1",
            "title": "Reply validation",
            "claim_description": "The monitor distinguishes forged reply-like frames.",
            "technical_reporter": "External Auditor",
            "method": "Dynamic bus validation",
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

    def test_workspace_help_wiki_and_version(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Assessment workspace", response.data)
        self.assertIn(b"SpaceCAN Assessment", response.data)

        help_response = self.client.get("/help/search?q=scope")
        self.assertEqual(help_response.status_code, 200)
        self.assertIn(b"Scope", help_response.data)

        wiki_response = self.client.get("/wiki")
        self.assertEqual(wiki_response.status_code, 200)
        self.assertIn(b"FARI specification", wiki_response.data)
        self.assertIn(b"Simple worked example", wiki_response.data)
        self.assertEqual(FARI_VERSION, "1.3.0")
        self.assertEqual(FARI_GENERATED_WITH, "FARI v1.3.0")

    def test_language_switch_dictionary_and_localized_report(self):
        response = self.client.get(
            "/language?language=es&next=/", follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Lista de evaluaciones", response.data)
        self.assertIn(b"Idioma", response.data)

        dictionary_response = self.client.get("/language/dictionary")
        self.assertEqual(dictionary_response.status_code, 200)
        self.assertIn(b"Diccionario de idioma editable", dictionary_response.data)
        self.assertIn(b"english_exception", dictionary_response.data)

        asset_response = self.client.get("/assets/1")
        self.assertEqual(asset_response.status_code, 200)
        self.assertIn(b"Fuentes del activo", asset_response.data)
        self.assertIn(b"Agregar fuente al activo", asset_response.data)

        report_response = self.client.get("/investigations/1/report.docx")
        self.assertEqual(report_response.status_code, 200)
        with zipfile.ZipFile(BytesIO(report_response.data)) as archive:
            document_xml = archive.read("word/document.xml")
        self.assertIn("Informe de investigación".encode(), document_xml)

    def test_operational_leo_reset_replay_scenario(self):
        assessment_response = self.client.post(
            "/assessments/new",
            data={
                "client_name": "Asterion Orbital Operations",
                "title": "Operational LEO Reset Command Replay",
                "mission_context": "Operational low-Earth-orbit contact window with a flight-computer command receiver.",
                "scope": "2026-05-14 operational contact event, RF capture, satellite logs, station reconciliation, and same-firmware engineering-model replay.",
                "authorization": "Authorized retrospective investigation of an operational command event.",
                "exclusions": "Backup-station completeness, physical transmitter attribution, and flight-vehicle laboratory reproduction.",
            },
            follow_redirects=True,
        )
        self.assertEqual(assessment_response.status_code, 200)

        with self.app.app_context():
            assessment = Assessment.query.filter_by(
                title="Operational LEO Reset Command Replay"
            ).one()
            assessment_id = assessment.id

        satellite_response = self.client.post(
            f"/assessments/{assessment_id}/assets",
            data={
                "name": "Operational LEO satellite flight computer",
                "description": "Operational spacecraft flight computer and CCSDS command receiver.",
                "segment": "space",
                "access_model": "private",
                "coverage": "reviewed",
            },
            follow_redirects=True,
        )
        self.assertEqual(satellite_response.status_code, 200)
        ground_response = self.client.post(
            f"/assessments/{assessment_id}/assets",
            data={
                "name": "LEO contact ground-station network",
                "description": "Primary and backup ground stations for the scheduled contact window.",
                "segment": "ground",
                "access_model": "private",
                "coverage": "reviewed",
            },
            follow_redirects=True,
        )
        self.assertEqual(ground_response.status_code, 200)

        with self.app.app_context():
            assessment = db.session.get(Assessment, assessment_id)
            satellite = next(
                asset
                for asset in assessment.assets
                if asset.name == "Operational LEO satellite flight computer"
            )

        investigation_response = self.client.post(
            f"/assessments/{assessment_id}/investigations/new",
            data={
                "asset_id": str(satellite.id),
                "title": "Unauthenticated flight-computer reset command execution",
                "claim_description": "The operational command path rejects unauthenticated or replayed reset commands and preserves sufficient attribution to distinguish authorized commanding from an injected transmission.",
                "technical_reporter": "FARI incident investigation team",
                "method": "Operational RF capture and satellite-log correlation, operations-plan reconciliation, and controlled same-firmware replay on an engineering model.",
                "environment": "Operational LEO contact window plus same-firmware laboratory replay on an engineering model.",
            },
            follow_redirects=True,
        )
        self.assertEqual(investigation_response.status_code, 200)

        with self.app.app_context():
            investigation = Investigation.query.filter_by(
                title="Unauthenticated flight-computer reset command execution"
            ).one()
            investigation_id = investigation.id

        investigation_response = self.client.post(
            f"/investigations/{investigation_id}/edit",
            data={
                "asset_id": str(satellite.id),
                "title": "Unauthenticated flight-computer reset command execution",
                "claim_description": "The operational command path rejects unauthenticated or replayed reset commands and preserves sufficient attribution to distinguish authorized commanding from an injected transmission.",
                "technical_reporter": "FARI incident investigation team",
                "method": "Operational RF capture and satellite-log correlation, operations-plan reconciliation, and controlled same-firmware replay on an engineering model.",
                "environment": "Operational LEO contact window plus same-firmware laboratory replay on an engineering model.",
                "facts": "The event occurred on 2026-05-14 at 10:01:30 UTC during a scheduled contact window with an operational LEO satellite.\nA valid CCSDS reset command was received, accepted, and executed.\nTelemetry was interrupted for eight minutes.\nA same-firmware engineering-model test reproduced the reset on 5 of 5 attempts.",
                "assertions": "The command dictionary identifies APID 0x042 as the flight-computer reset command.",
                "inferences": "The operational command path accepted and executed a reset command without an evidenced cryptographic authenticity or freshness check.",
                "assumptions": "The supplied satellite execution log is synchronized to UTC.",
                "contradictions": "The satellite execution log records an accepted command, but the command is absent from the approved operations plan and primary station transmission log.",
                "gaps": "Backup-station logs were not provided. A single RF capture cannot determine the physical transmitter. The laboratory target was an engineering model, not the flight vehicle.",
                "technical_sufficiency": "sufficient",
                "reachability_sufficiency": "partial",
                "mission_sufficiency": "partial",
                "conclusion": "does_not_meet",
                "scenario_state": "demonstrated",
                "confidence": "medium",
                "required_action": "remediate",
                "priority": "immediate",
                "scope_boundary": "The 2026-05-14 operational LEO contact event and same-firmware engineering-model replay; backup-station completeness, physical transmitter attribution, and flight-vehicle laboratory reproduction remain outside the evidenced boundary.",
                "rationale": "The operational execution and eight-minute telemetry interruption demonstrate that the claim fails within the declared event scope.",
                "recommendations": "Implement cryptographic command authentication and anti-replay controls. Preserve synchronized logs from every ground station. Retest on flight-representative hardware and the operational RF chain.",
                "acceptance_criteria": "An unauthenticated or replayed reset frame is rejected and logged as an integrity event.",
                "status": "ready",
                "gating": "on",
            },
            follow_redirects=True,
        )
        self.assertEqual(investigation_response.status_code, 200)

        evidence_root = Path(__file__).resolve().parents[1] / "cases" / "05_evidence"
        evidence_files = sorted(evidence_root.glob("*.txt"))
        self.assertEqual(len(evidence_files), 4)
        for evidence_file in evidence_files:
            response = self.client.post(
                f"/investigations/{investigation_id}/evidence",
                data={
                    "description": f"Scenario evidence: {evidence_file.name}",
                    "file": (BytesIO(evidence_file.read_bytes()), evidence_file.name),
                },
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)

        finding_response = self.client.post(
            f"/investigations/{investigation_id}/findings",
            data={
                "title": "Unauthenticated reset command was accepted and executed",
                "state": "confirmed",
                "condition_text": "The operational command receiver accepted and executed a valid CCSDS reset command without an evidenced authentication or replay check.",
                "observed_effect": "The flight-computer reset counter increased and telemetry was interrupted for eight minutes.",
                "credible_impact": "An injected or replayed command can disrupt commandability and telemetry availability during operations.",
                "mapping_state": "candidate",
                "mapping_rationale": "No external framework mapping is required to establish the FARI claim failure.",
            },
            follow_redirects=True,
        )
        self.assertEqual(finding_response.status_code, 200)

        detail_response = self.client.get(
            f"/investigations/{investigation_id}", follow_redirects=True
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertIn(b"Does Not Meet", detail_response.data)
        self.assertIn(b"Scenario: Demonstrated", detail_response.data)

        with self.app.app_context():
            investigation = db.session.get(Investigation, investigation_id)
            self.assertIn("2026-05-14 at 10:01:30 UTC", investigation.facts)
            self.assertIn("engineering-model", investigation.scope_boundary)
            self.assertEqual(investigation.scenario_state, "demonstrated")
            self.assertEqual(investigation.conclusion, "does_not_meet")
            self.assertEqual(len(investigation.evidence), 4)
            self.assertEqual(len(investigation.findings), 1)
            self.assertTrue(all(item.sha256 for item in investigation.evidence))
    def test_login_required_and_resources_are_current(self):
        anonymous = self.app.test_client()
        response = anonymous.get("/", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Access the workspace", response.data)

        resources = self.client.get("/resources")
        self.assertEqual(resources.status_code, 200)
        self.assertIn(b"Reference material and downloadables", resources.data)
        self.assertIn(b"Assessment JSON schema", resources.data)
        self.assertNotIn(b"companion", resources.data.lower())

    def test_finding_report_and_export_use_framework_neutral_fields(self):
        self.client.post(
            "/investigations/1/findings",
            data={
                "title": "Forged frame influences displayed telemetry",
                "state": "confirmed",
                "condition_text": "The display accepts attacker-controlled frame data.",
                "observed_effect": "The displayed value changed.",
                "credible_impact": "Operators could receive misleading state.",
                "mapping_state": "confirmed",
                "mapping_rationale": "The finding is directly linked to the claim.",
            },
        )
        response = self.client.get("/investigations/1/report.docx")
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(BytesIO(response.data)) as archive:
            document_xml = archive.read("word/document.xml")
        self.assertIn(b"Normalized Findings", document_xml)
        self.assertIn(b"Framework mapping", self.client.get("/investigations/1").data)

        exported = self.client.get("/assessments/1/export.json")
        payload = json.loads(exported.data)
        self.assertEqual(payload["generated_with"], "FARI v1.3.0")
        self.assertNotIn("compliance_profiles", payload)
        removed_finding_key = "sp" + "arta_id"
        self.assertNotIn(removed_finding_key, payload["investigations"][0]["findings"][0])

    def test_removed_modules_have_no_public_routes(self):
        catalog_route = "/" + "sp" + "arta/ttps"
        profile_route = "/assessments/1/compliance/" + "sp" + "d5-companion"
        self.assertEqual(self.client.get(catalog_route).status_code, 404)
        self.assertEqual(self.client.get(profile_route).status_code, 404)

        self.assertEqual(self.client.get("/attack-flows/1").status_code, 404)
        self.assertEqual(
            self.client.post("/assessments/1/attack-flows").status_code,
            404,
        )
        exported = json.loads(self.client.get("/assessments/1/export.json").data)
        self.assertNotIn("attack_flows", exported)

    def test_traceability_and_asset_sources(self):
        response = self.client.post(
            "/assessments/1/versions/capture",
            data={"summary": "Initial framing snapshot."},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Revision v1 captured", response.data)

        response = self.client.post(
            "/assets/1/sources",
            data={
                "file": (BytesIO(b"libfoo==1.4.2\nrequests==2.31.0\n"), "requirements.txt"),
                "notes": "Baseline software inventory.",
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Asset source SRC-0001-001 preserved", response.data)
        self.assertIn(b"libfoo", response.data)

        jsonl_payload = (
            b'{"timestamp":"2026-05-14T09:55:00Z","source":"mission-schedule",'
            b'"event\\_type":"contact\\_window","asset":"Aurora-EO",'
            b'"detail":"Approved contact window opened."}\n'
            b'{"timestamp":"2026-05-14T10:01:30Z","source":"spacecraft-telemetry",'
            b'"event\\_type":"command\\_executed","asset":"Aurora-EO OBC",'
            b'"detail":"Reset command executed."}\n\\\n'
        )
        parsed_jsonl = parse_asset_source("operational-log.jsonl", jsonl_payload)
        self.assertEqual(parsed_jsonl["format"], "jsonl")
        self.assertEqual(parsed_jsonl["record_count"], 2)
        response = self.client.post(
            "/assets/1/sources",
            data={
                "file": (BytesIO(jsonl_payload), "operational-log.jsonl"),
                "notes": "Operational JSONL event log.",
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"operational-log.jsonl", response.data)
        self.assertIn(b"JSONL event log", response.data)

        for payload, filename, marker in [
            (b"\x00\x01\x02\xffFARI", "flight-computer.bin", b"Binary sample"),
            (b'{"global":{"core:sample_rate":2000000},"captures":[]}', "capture.sigmf-meta", b"SigMF metadata"),
            (b"\x00\x01\x02\x03", "capture.sigmf-data", b"SigMF data"),
        ]:
            response = self.client.post(
                "/assets/1/sources",
                data={"file": (BytesIO(payload), filename)},
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(marker, response.data)

        with self.app.app_context():
            sources = AssetSource.query.filter_by(asset_id=1).order_by(AssetSource.id).all()
            self.assertEqual(len(sources), 5)
            self.assertEqual(
                [source.file_format for source in sources],
                ["text-list", "jsonl", "binary", "sigmf-meta", "sigmf-data"],
            )
            self.assertTrue(all(source.sha256 and source.byte_size >= 0 for source in sources))

        traceability = self.client.get("/assessments/1/traceability")
        self.assertEqual(traceability.status_code, 200)
        self.assertIn(b"Current working state", traceability.data)


if __name__ == "__main__":
    unittest.main()
