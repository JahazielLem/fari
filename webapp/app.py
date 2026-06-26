"""FARI guided assessment and reporting web application."""

from __future__ import annotations

import hmac
import hashlib
import json
import os
import shutil
from datetime import date
from io import BytesIO
from pathlib import Path

from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from werkzeug.utils import secure_filename

from webapp.attack_flow import AttackFlowError, parse_attack_flow
from webapp.compliance import (
    SPD5_COMPANION_KEY,
    SPD5_COMPANION_REFERENCE_URL,
    SPD5_SCENARIOS,
    SPD5_STATUS_OPTIONS,
    family_groups_for_profile,
    find_profile_by_key,
    scenario_by_slug,
    seed_spd5_companion,
    status_counts,
    sync_profile_posture,
)
from webapp.db import (
    Assessment,
    AssessmentVersion,
    Asset,
    AttackFlow,
    Evidence,
    Finding,
    InventoryComponent,
    InventoryEvent,
    Investigation,
    SbomDocument,
    db,
    init_app as init_db,
    next_sequence,
    now_iso,
)
from webapp.meta import FARI_GENERATED_WITH, FARI_VERSION
from webapp.reporting import (
    build_consolidated_pdf,
    build_consolidated_report,
    build_investigation_pdf,
    build_investigation_report,
    human,
    overall_conclusion,
)
from webapp.sbom import parse_sbom_bytes
from webapp.sparta_parser import countermeasures_for, load_sparta_catalog, search_ttps
from webapp.traceability import (
    capture_assessment_version,
    current_snapshot_reference,
    diff_snapshots,
    latest_revision_label,
    parse_version_snapshot,
)
from webapp.wiki import (
    load_specification_html,
    load_specification_outline,
    search_definitions,
)


INVESTIGATION_FIELDS = [
    "asset_id",
    "title",
    "claim_description",
    "technical_reporter",
    "method",
    "environment",
    "facts",
    "assertions",
    "inferences",
    "assumptions",
    "contradictions",
    "gaps",
    "technical_sufficiency",
    "reachability_sufficiency",
    "mission_sufficiency",
    "conclusion",
    "scenario_state",
    "confidence",
    "required_action",
    "priority",
    "scope_boundary",
    "rationale",
    "recommendations",
    "acceptance_criteria",
]

FINDING_FIELDS = [
    "title",
    "state",
    "condition_text",
    "observed_effect",
    "credible_impact",
    "sparta_id",
    "sparta_name",
    "mapping_state",
    "mapping_rationale",
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_ROOT = PROJECT_ROOT / "spec"
SPEC_RELEASES_ROOT = SPEC_ROOT / "releases"
SPEC_SCHEMA_ROOT = SPEC_ROOT / "schema"
RELEASE_ROOT = SPEC_RELEASES_ROOT / f"v{FARI_VERSION}"
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Sign in to continue working in FARI."
login_manager.login_message_category = "error"


class FariUser(UserMixin):
    def __init__(self, username: str):
        self.id = username


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def create_app(test_config=None):
    app = Flask(__name__)
    data_dir = Path(os.environ.get("FARI_DATA_DIR", Path.cwd() / "instance"))
    database_url = os.environ.get("FARI_DATABASE_URL") or os.environ.get("DATABASE_URL")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FARI_SECRET_KEY", "fari-local-development"),
        DATABASE=str(data_dir / "fari.sqlite3"),
        SQLALCHEMY_DATABASE_URI=normalize_database_url(database_url)
        if database_url
        else None,
        UPLOAD_DIR=str(data_dir / "evidence"),
        ATTACK_FLOW_DIR=str(data_dir / "attack_flows"),
        SBOM_DIR=str(data_dir / "sbom"),
        FARI_LOGIN_USERNAME=os.environ.get("FARI_LOGIN_USERNAME", "fari"),
        FARI_LOGIN_PASSWORD=os.environ.get("FARI_LOGIN_PASSWORD", "toor"),
        FARI_REPOSITORY_URL=os.environ.get("FARI_REPOSITORY_URL", ""),
        FARI_BRAND_IMAGE_URL=os.environ.get("FARI_BRAND_IMAGE_URL", ""),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
        database_parent = Path(app.config["DATABASE"]).parent
        if "SBOM_DIR" not in test_config:
            app.config["SBOM_DIR"] = str(database_parent / "sbom")
        if "DATABASE" in test_config and "SQLALCHEMY_DATABASE_URI" not in test_config:
            app.config["SQLALCHEMY_DATABASE_URI"] = None
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + app.config["DATABASE"]
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_url(
            app.config["SQLALCHEMY_DATABASE_URI"]
        )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {"pool_pre_ping": True})
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["ATTACK_FLOW_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["SBOM_DIR"]).mkdir(parents=True, exist_ok=True)
    init_db(app)
    login_manager.init_app(app)

    app.jinja_env.filters["human"] = human
    app.jinja_env.globals["fari_generated_with"] = FARI_GENERATED_WITH
    app.jinja_env.globals["fari_version"] = FARI_VERSION
    app.jinja_env.globals["fari_repository_url"] = app.config["FARI_REPOSITORY_URL"]
    app.jinja_env.globals["fari_brand_image_url"] = app.config["FARI_BRAND_IMAGE_URL"]
    app.jinja_env.globals["form_value"] = lambda name, default="": (
        request.form.get(name, default) if request.method == "POST" else default
    )
    app.jinja_env.globals["form_checked"] = lambda name, default=False: (
        name in request.form if request.method == "POST" else default
    )

    def release_file(*parts: str) -> Path:
        current = RELEASE_ROOT.joinpath(*parts)
        if current.exists():
            return current
        for releases_root in (SPEC_RELEASES_ROOT, PROJECT_ROOT / "releases"):
            if not releases_root.exists():
                continue
            for root in sorted(releases_root.glob("v*"), reverse=True):
                candidate = root.joinpath(*parts)
                if candidate.exists():
                    return candidate
        return current

    resource_catalog = [
        {
            "slug": "specification",
            "label": "FARI specification",
            "description": "Versioned PDF specification with workflow, glossary, examples, and the SPD-5 companion appendix.",
            "path": release_file("specification", f"FARI-Specification-v{FARI_VERSION}.pdf"),
            "download_name": f"FARI-Specification-v{FARI_VERSION}.pdf",
        },
        {
            "slug": "manual-template",
            "label": "Manual fill template",
            "description": "Versioned PDF template aligned with the finalized workflow and field names.",
            "path": release_file("manual-template", f"FARI-Manual-Template-v{FARI_VERSION}.pdf"),
            "download_name": f"FARI-Manual-Template-v{FARI_VERSION}.pdf",
        },
        {
            "slug": "scenario-catalog",
            "label": "Scenario test catalog",
            "description": "Versioned PDF catalog of seeded FARI and SPD-5 companion scenarios used to validate the framework.",
            "path": release_file("reports", f"FARI-SCENARIO-TEST_CATALOG-v{FARI_VERSION}.pdf"),
            "download_name": f"FARI-SCENARIO-TEST_CATALOG-v{FARI_VERSION}.pdf",
        },
        {
            "slug": "schema",
            "label": "Assessment JSON schema",
            "description": "Machine-readable contract for exports and integrations.",
            "path": SPEC_SCHEMA_ROOT / "fari-assessment.schema.json",
            "download_name": "fari-assessment.schema.json",
        },
        {
            "slug": "spd5-companion",
            "label": "SPD-5 companion profile",
            "description": "Compliance overlay guidance, scenarios, and control families tied back to FARI evidence.",
            "path": release_file("_sources", "specification", "FARI-SPD5-COMPANION.md"),
            "download_name": "FARI-SPD5-COMPANION.md",
        },
    ]
    resources_by_slug = {item["slug"]: item for item in resource_catalog}

    @login_manager.user_loader
    def load_user(user_id):
        if user_id == app.config["FARI_LOGIN_USERNAME"]:
            return FariUser(user_id)
        return None

    def safe_redirect_target(value: str | None) -> str:
        if value and value.startswith("/") and not value.startswith("//"):
            return value
        return url_for("index")

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for("login", next=request.full_path if request.query_string else request.path))

    @app.before_request
    def require_workspace_login():
        endpoint = request.endpoint or ""
        if endpoint in {"login", "static"}:
            return None
        if current_user.is_authenticated:
            return None
        return redirect(url_for("login", next=request.full_path if request.query_string else request.path))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        next_target = request.args.get("next") or request.form.get("next")
        if current_user.is_authenticated:
            return redirect(safe_redirect_target(next_target))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            valid_username = hmac.compare_digest(
                username, app.config["FARI_LOGIN_USERNAME"]
            )
            valid_password = hmac.compare_digest(
                password, app.config["FARI_LOGIN_PASSWORD"]
            )
            if valid_username and valid_password:
                login_user(FariUser(username))
                flash("Workspace access granted.", "success")
                return redirect(safe_redirect_target(next_target))
            flash("Invalid credentials.", "error")
        return render_template("login.html", next_target=safe_redirect_target(next_target))

    @app.post("/logout")
    def logout():
        logout_user()
        flash("Signed out from the workspace.", "success")
        return redirect(url_for("login"))

    @app.get("/")
    def index():
        status_filter = request.args.get("status", "all").strip().lower()
        result_filter = request.args.get("result", "all").strip().lower()
        limit = _integer_or_none(request.args.get("limit")) or 25
        if status_filter not in {"all", "draft", "closed"}:
            status_filter = "all"
        if result_filter not in {
            "all",
            "meets",
            "does_not_meet",
            "inconclusive",
            "not_assessed",
        }:
            result_filter = "all"
        if limit not in {10, 25, 50, 100}:
            limit = 25
        assessments = db.session.scalars(
            select(Assessment)
            .options(selectinload(Assessment.assets), selectinload(Assessment.investigations))
            .order_by(Assessment.updated_at.desc(), Assessment.created_at.desc())
        ).all()
        summaries = build_assessment_summaries(assessments)
        filtered = [
            summary
            for summary in summaries
            if (status_filter == "all" or summary["assessment"].status == status_filter)
            and (result_filter == "all" or summary["result"] == result_filter)
        ]
        stats = {
            "total": len(summaries),
            "draft": sum(item["assessment"].status == "draft" for item in summaries),
            "closed": sum(item["assessment"].status == "closed" for item in summaries),
            "filtered": len(filtered),
        }
        return render_template(
            "index.html",
            summaries=filtered[:limit],
            filters={
                "status": status_filter,
                "result": result_filter,
                "limit": limit,
            },
            stats=stats,
        )

    @app.get("/wiki")
    def wiki():
        return render_template(
            "wiki.html",
            spec_html=load_specification_html(),
            outline=load_specification_outline(),
        )

    @app.get("/resources")
    def resources():
        return render_template(
            "resources.html",
            resources=resource_catalog,
            repository_url=app.config["FARI_REPOSITORY_URL"],
        )

    @app.get("/resources/download/<slug>")
    def download_resource(slug):
        resource = resources_by_slug.get(slug)
        if resource is None or not resource["path"].exists():
            abort(404)
        return send_file(
            resource["path"],
            as_attachment=True,
            download_name=resource["download_name"],
        )

    @app.route("/assessments/new", methods=["GET", "POST"])
    def new_assessment():
        if request.method == "POST":
            client_name = request.form.get("client_name", "").strip()
            title = request.form.get("title", "").strip()
            if not client_name or not title:
                flash("Client name and assessment title are required.", "error")
                return render_template(
                    "assessment_form.html", phases=new_assessment_phases()
                )
            assessment = Assessment(
                client_name=client_name,
                title=title,
                mission_context=request.form.get("mission_context", "").strip(),
                scope=request.form.get("scope", "").strip(),
                authorization=request.form.get("authorization", "").strip(),
                exclusions=request.form.get("exclusions", "").strip(),
                report_author="Fari-Agent",
            )
            db.session.add(assessment)
            db.session.flush()
            assessment.fari_id = f"ASM-{date.today().year}-{assessment.id:04d}"
            db.session.commit()
            flash("Frame created. Register assets and open investigations.", "success")
            return redirect(url_for("assessment_detail", assessment_id=assessment.id))
        return render_template("assessment_form.html", phases=new_assessment_phases())

    @app.get("/assessments/<int:assessment_id>")
    def assessment_detail(assessment_id):
        assessment = get_assessment(assessment_id)
        checks = assessment_checks(assessment)
        spd5_profile = find_profile_by_key(assessment, SPD5_COMPANION_KEY)
        return render_template(
            "assessment_detail.html",
            assessment=assessment,
            assets=assessment.assets,
            investigations=assessment.investigations,
            attack_flows=assessment.attack_flows,
            sbom_documents=assessment.sbom_documents,
            inventory_components=assessment.inventory_components,
            overall=overall_conclusion(assessment.investigations),
            checks=checks,
            phases=assessment_phases(assessment),
            revision_label=latest_revision_label(assessment),
            spd5_profile=spd5_profile,
            spd5_counts=status_counts(spd5_profile.checks) if spd5_profile else {},
            spd5_scenario=scenario_by_slug(spd5_profile.scenario) if spd5_profile else None,
        )

    @app.get("/assessments/<int:assessment_id>/traceability")
    def assessment_traceability(assessment_id):
        assessment = get_assessment(assessment_id)
        versions = sorted(assessment.versions, key=lambda item: item.version_number, reverse=True)
        compare_options = [
            {
                "id": "current",
                "label": "Current working state",
                "summary": "Live assessment state",
                "trigger": "live_state",
                "created_at": assessment.updated_at,
            }
        ] + [
            {
                "id": str(version.id),
                "label": version.label,
                "summary": version.summary,
                "trigger": version.trigger,
                "created_at": version.created_at,
                "fari_id": version.fari_id,
            }
            for version in versions
        ]

        base_ref, target_ref = default_traceability_refs(assessment, versions)
        base_ref = request.args.get("base", base_ref)
        target_ref = request.args.get("target", target_ref)
        base_version = resolve_snapshot_ref(assessment, versions, base_ref)
        target_version = resolve_snapshot_ref(assessment, versions, target_ref)
        diff = None
        if base_version and target_version and base_version["id"] != target_version["id"]:
            diff = diff_snapshots(base_version["snapshot"], target_version["snapshot"])

        return render_template(
            "assessment_traceability.html",
            assessment=assessment,
            versions=versions,
            compare_options=compare_options,
            base_version=base_version,
            target_version=target_version,
            diff=diff,
            phases=assessment_phases(assessment),
        )

    @app.post("/assessments/<int:assessment_id>/compliance/spd5-companion/create")
    def create_spd5_companion(assessment_id):
        assessment = get_assessment(assessment_id)
        ensure_assessment_open(assessment)
        profile = find_profile_by_key(assessment, SPD5_COMPANION_KEY)
        if profile is None:
            profile = seed_spd5_companion(assessment)
            db.session.add(profile)
            touch_assessment(assessment)
            db.session.commit()
            flash(
                "SPD-5 companion profile created. Map controls to FARI evidence as needed.",
                "success",
            )
        return redirect(url_for("assessment_spd5_companion", assessment_id=assessment_id))

    @app.route(
        "/assessments/<int:assessment_id>/compliance/spd5-companion",
        methods=["GET", "POST"],
    )
    def assessment_spd5_companion(assessment_id):
        assessment = get_assessment(assessment_id)
        profile = find_profile_by_key(assessment, SPD5_COMPANION_KEY)
        if profile is None:
            return render_template(
                "compliance_profile.html",
                assessment=assessment,
                profile=None,
                groups=[],
                counts={option: 0 for option in SPD5_STATUS_OPTIONS},
                scenarios=SPD5_SCENARIOS,
                status_options=SPD5_STATUS_OPTIONS,
                reference_url=SPD5_COMPANION_REFERENCE_URL,
                phases=assessment_phases(assessment),
            )
        if request.method == "POST":
            ensure_assessment_open(assessment)
            submitted_scenario = request.form.get("scenario", "").strip()
            if scenario_by_slug(submitted_scenario):
                profile.scenario = submitted_scenario
            profile.summary = request.form.get("summary", "").strip()
            profile.notes = request.form.get("notes", "").strip()
            for check in profile.checks:
                submitted_status = request.form.get(f"status_{check.id}", "").strip()
                check.status = (
                    submitted_status
                    if submitted_status in SPD5_STATUS_OPTIONS
                    else "not_verified"
                )
                check.evidence_refs = request.form.get(
                    f"evidence_refs_{check.id}", ""
                ).strip()
                check.notes = request.form.get(f"notes_{check.id}", "").strip()
                check.updated_at = now_iso()
            sync_profile_posture(profile)
            touch_assessment(assessment)
            db.session.commit()
            flash("SPD-5 companion checklist saved.", "success")
            return redirect(
                url_for("assessment_spd5_companion", assessment_id=assessment_id)
            )
        return render_template(
            "compliance_profile.html",
            assessment=assessment,
            profile=profile,
            groups=family_groups_for_profile(profile),
            counts=status_counts(profile.checks),
            scenarios=SPD5_SCENARIOS,
            status_options=SPD5_STATUS_OPTIONS,
            reference_url=SPD5_COMPANION_REFERENCE_URL,
            phases=assessment_phases(assessment),
        )

    @app.post("/assessments/<int:assessment_id>/versions/capture")
    def capture_version(assessment_id):
        assessment = get_assessment(assessment_id)
        summary = request.form.get("summary", "").strip() or "Manual traceability snapshot."
        db.session.add(
            capture_assessment_version(
                assessment,
                trigger="manual_snapshot",
                summary=summary,
            )
        )
        assessment.updated_at = now_iso()
        db.session.commit()
        flash(f"Revision {latest_revision_label(assessment)} captured.", "success")
        return redirect(url_for("assessment_traceability", assessment_id=assessment_id))

    @app.post("/assessments/<int:assessment_id>/delete")
    def delete_assessment(assessment_id):
        assessment = get_assessment(assessment_id)
        ensure_assessment_open(assessment)
        fari_id = assessment.fari_id
        investigation_ids = [item.fari_id for item in assessment.investigations]
        db.session.delete(assessment)
        db.session.commit()
        for investigation_id in investigation_ids:
            shutil.rmtree(Path(app.config["UPLOAD_DIR"]) / investigation_id, ignore_errors=True)
        shutil.rmtree(Path(app.config["ATTACK_FLOW_DIR"]) / fari_id, ignore_errors=True)
        flash(f"Assessment {fari_id} and its open working data were deleted.", "success")
        return redirect(url_for("index"))

    @app.post("/assessments/<int:assessment_id>/status")
    def update_assessment_status(assessment_id):
        assessment = get_assessment(assessment_id)
        action = request.form.get("action")
        if assessment.status == "closed":
            flash("This assessment is closed and immutable.", "error")
        elif action == "close":
            checks = assessment_checks(assessment)
            missing = [check["label"] for check in checks if not check["done"]]
            if missing:
                flash("Assessment cannot close yet: " + ", ".join(missing) + ".", "error")
            else:
                assessment.status = "closed"
                assessment.maturity = "final"
                assessment.updated_at = now_iso()
                db.session.add(
                    capture_assessment_version(
                        assessment,
                        trigger="assessment_closed",
                        summary="Assessment closed and final report published.",
                    )
                )
                db.session.commit()
                flash("Assessment closed. The consolidated report is final for this scope.", "success")
        return redirect(url_for("assessment_detail", assessment_id=assessment_id))

    @app.post("/assessments/<int:assessment_id>/assets")
    def add_asset(assessment_id):
        assessment = get_assessment(assessment_id)
        ensure_assessment_open(assessment)
        name = request.form.get("name", "").strip()
        if not name:
            flash("Asset name is required.", "error")
            return redirect(url_for("assessment_detail", assessment_id=assessment_id))
        sequence = next_sequence(assessment.assets, "AST")
        asset = Asset(
            assessment=assessment,
            fari_id=f"AST-{assessment_id:04d}-{sequence:03d}",
            name=name,
            segment=request.form.get("segment", "space"),
            description=request.form.get("description", "").strip(),
            access_model=request.form.get("access_model", "private"),
            coverage=request.form.get("coverage", "not_assessed"),
        )
        touch_assessment(assessment)
        db.session.add(asset)
        db.session.commit()
        flash(f"Asset {asset.fari_id} added.", "success")
        return redirect(url_for("assessment_detail", assessment_id=assessment_id))

    @app.post("/assets/<int:asset_id>/delete")
    def delete_asset(asset_id):
        asset = get_record(Asset, asset_id)
        assessment = asset.assessment
        ensure_assessment_open(assessment)
        assessment_id = assessment.id
        fari_id = asset.fari_id
        for investigation in list(asset.investigations):
            investigation.asset_id = None
        for document in list(asset.sbom_documents):
            document.asset_id = None
        for component in list(asset.inventory_components):
            component.asset_id = None
        db.session.delete(asset)
        touch_assessment(assessment)
        db.session.commit()
        flash(
            f"Asset {fari_id} deleted. Related investigations and inventory records kept their history.",
            "success",
        )
        return redirect(url_for("assessment_detail", assessment_id=assessment_id))

    @app.route("/assessments/<int:assessment_id>/investigations/new", methods=["GET", "POST"])
    def new_investigation(assessment_id):
        assessment = get_assessment(assessment_id)
        ensure_assessment_open(assessment)
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            claim_description = request.form.get("claim_description", "").strip()
            if not title or not claim_description:
                flash("Investigation title and claim description are required.", "error")
                return render_template(
                    "investigation_form.html",
                    assessment=assessment,
                    assets=assessment.assets,
                    investigation=None,
                    phases=assessment_phases(assessment),
                )
            sequence = next_sequence(assessment.investigations, "INV")
            investigation = Investigation(
                assessment=assessment,
                asset_id=_integer_or_none(request.form.get("asset_id")),
                fari_id=f"INV-{assessment_id:04d}-{sequence:03d}",
                claim_id=f"CLM-{assessment_id:04d}-{sequence:03d}",
                title=title,
                claim_description=claim_description,
                gating=bool(request.form.get("gating")),
                technical_reporter=request.form.get("technical_reporter", "").strip(),
                method=request.form.get("method", "").strip(),
                environment=request.form.get("environment", "").strip(),
                scope_boundary=request.form.get("scope_boundary", "").strip(),
            )
            touch_assessment(assessment)
            db.session.add(investigation)
            db.session.commit()
            flash(
                f"Investigation {investigation.fari_id} and claim {investigation.claim_id} created.",
                "success",
            )
            return redirect(url_for("edit_investigation", investigation_id=investigation.id))
        return render_template(
            "investigation_form.html",
            assessment=assessment,
            assets=assessment.assets,
            investigation=None,
            phases=assessment_phases(assessment),
        )

    @app.route("/investigations/<int:investigation_id>/edit", methods=["GET", "POST"])
    def edit_investigation(investigation_id):
        investigation = get_investigation(investigation_id)
        if investigation.status == "closed" or investigation.assessment.status == "closed":
            flash("This investigation is closed and immutable.", "error")
            return redirect(url_for("investigation_detail", investigation_id=investigation_id))
        if request.method == "POST":
            error = validate_investigation_form(request.form)
            if error:
                flash(error, "error")
                return render_template(
                    "investigation_form.html",
                    assessment=investigation.assessment,
                    assets=investigation.assessment.assets,
                    investigation=investigation,
                    phases=assessment_phases(investigation.assessment),
                )
            for field in INVESTIGATION_FIELDS:
                value = request.form.get(field, "").strip()
                setattr(investigation, field, _integer_or_none(value) if field == "asset_id" else value)
            investigation.gating = bool(request.form.get("gating"))
            investigation.updated_at = now_iso()
            investigation.status = request.form.get("status", "draft")
            touch_assessment(investigation.assessment)
            db.session.commit()
            flash("Investigation saved.", "success")
            return redirect(url_for("investigation_detail", investigation_id=investigation_id))
        return render_template(
            "investigation_form.html",
            assessment=investigation.assessment,
            assets=investigation.assessment.assets,
            investigation=investigation,
            phases=assessment_phases(investigation.assessment),
        )

    @app.get("/investigations/<int:investigation_id>")
    def investigation_detail(investigation_id):
        investigation = get_investigation(investigation_id)
        return render_template(
            "investigation_detail.html",
            assessment=investigation.assessment,
            investigation=investigation,
            asset=investigation.asset,
            evidence=investigation.evidence,
            findings=investigation.findings,
            checks=investigation_checks(investigation),
            phases=assessment_phases(investigation.assessment),
        )

    @app.post("/investigations/<int:investigation_id>/status")
    def update_investigation_status(investigation_id):
        investigation = get_investigation(investigation_id)
        if investigation.status == "closed" or investigation.assessment.status == "closed":
            flash("This investigation is closed and immutable.", "error")
            return redirect(url_for("investigation_detail", investigation_id=investigation_id))
        action = request.form.get("action")
        if action == "ready":
            investigation.status = "ready"
            touch_assessment(investigation.assessment)
            flash("Investigation marked ready for closure review.", "success")
        elif action == "close":
            checks = investigation_checks(investigation)
            missing = [check["label"] for check in checks if not check["done"]]
            if missing:
                flash("Investigation cannot close yet: " + ", ".join(missing) + ".", "error")
                return redirect(url_for("investigation_detail", investigation_id=investigation_id))
            investigation.status = "closed"
            flash("Investigation closed. Its report is final for the declared scope.", "success")
        investigation.updated_at = now_iso()
        db.session.commit()
        return redirect(url_for("investigation_detail", investigation_id=investigation_id))

    @app.post("/investigations/<int:investigation_id>/delete")
    def delete_investigation(investigation_id):
        investigation = get_investigation(investigation_id)
        ensure_investigation_open(investigation)
        assessment = investigation.assessment
        assessment_id = assessment.id
        fari_id = investigation.fari_id
        claim_id = investigation.claim_id
        working_directory = Path(app.config["UPLOAD_DIR"]) / fari_id
        db.session.delete(investigation)
        touch_assessment(assessment)
        db.session.commit()
        shutil.rmtree(working_directory, ignore_errors=True)
        flash(
            f"Investigation {fari_id} and claim {claim_id} deleted from the draft workspace.",
            "success",
        )
        return redirect(url_for("assessment_detail", assessment_id=assessment_id))

    @app.post("/investigations/<int:investigation_id>/evidence")
    def add_evidence(investigation_id):
        investigation = get_investigation(investigation_id)
        ensure_investigation_open(investigation)
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            flash("Select an evidence file.", "error")
            return redirect(url_for("investigation_detail", investigation_id=investigation_id))
        original_name = secure_filename(uploaded.filename) or "evidence.bin"
        sequence = next_sequence(investigation.evidence, "EVD")
        fari_id = f"EVD-{investigation_id:04d}-{sequence:03d}"
        stored_name = f"{fari_id}-{original_name}"
        target = evidence_path(investigation, stored_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        uploaded.save(target)
        item = Evidence(
            investigation=investigation,
            fari_id=fari_id,
            filename=original_name,
            stored_name=stored_name,
            description=request.form.get("description", "").strip(),
            sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            mime_type=uploaded.mimetype or "",
        )
        db.session.add(item)
        touch_investigation(investigation)
        db.session.commit()
        flash(f"Evidence {fari_id} preserved with SHA-256.", "success")
        return redirect(url_for("investigation_detail", investigation_id=investigation_id))

    @app.get("/evidence/<int:evidence_id>/download")
    def download_evidence(evidence_id):
        item = get_record(Evidence, evidence_id)
        path = evidence_path(item.investigation, item.stored_name)
        if not path.exists():
            abort(404)
        return send_file(path, as_attachment=True, download_name=item.filename)

    @app.post("/evidence/<int:evidence_id>/delete")
    def delete_evidence(evidence_id):
        item = get_record(Evidence, evidence_id)
        investigation = item.investigation
        ensure_investigation_open(investigation)
        path = evidence_path(investigation, item.stored_name)
        if path.exists():
            path.unlink()
        db.session.delete(item)
        touch_investigation(investigation)
        db.session.commit()
        flash(f"Evidence {item.fari_id} deleted.", "success")
        return redirect(url_for("investigation_detail", investigation_id=investigation.id))

    @app.post("/investigations/<int:investigation_id>/findings")
    def add_finding(investigation_id):
        investigation = get_investigation(investigation_id)
        ensure_investigation_open(investigation)
        title = request.form.get("title", "").strip()
        if not title:
            flash("Finding title is required.", "error")
            return redirect(url_for("investigation_detail", investigation_id=investigation_id))
        sequence = next_sequence(investigation.findings, "FND")
        finding = Finding(
            investigation=investigation,
            fari_id=f"FND-{investigation_id:04d}-{sequence:03d}",
            **finding_values(request.form),
        )
        db.session.add(finding)
        touch_investigation(investigation)
        db.session.commit()
        flash(f"Finding {finding.fari_id} added.", "success")
        return redirect(url_for("investigation_detail", investigation_id=investigation_id))

    @app.route("/findings/<int:finding_id>/edit", methods=["GET", "POST"])
    def edit_finding(finding_id):
        finding = get_record(Finding, finding_id)
        if finding.investigation.status == "closed" or finding.investigation.assessment.status == "closed":
            flash("This finding belongs to a closed, immutable investigation.", "error")
            return redirect(
                url_for("investigation_detail", investigation_id=finding.investigation_id)
            )
        if request.method == "POST":
            values = finding_values(request.form)
            if not values["title"]:
                flash("Finding title is required.", "error")
            else:
                for field, value in values.items():
                    setattr(finding, field, value)
                touch_investigation(finding.investigation)
                db.session.commit()
                flash(f"Finding {finding.fari_id} and its SPARTA mapping were updated.", "success")
                return redirect(
                    url_for("investigation_detail", investigation_id=finding.investigation_id)
                )
        return render_template(
            "finding_form.html",
            finding=finding,
            investigation=finding.investigation,
            assessment=finding.investigation.assessment,
            phases=assessment_phases(finding.investigation.assessment),
        )

    @app.post("/assessments/<int:assessment_id>/attack-flows")
    def add_attack_flow(assessment_id):
        assessment = get_assessment(assessment_id)
        ensure_assessment_open(assessment)
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            flash("Select an AFB file.", "error")
            return redirect(url_for("assessment_detail", assessment_id=assessment_id))
        original_name = secure_filename(uploaded.filename) or "attack-flow.afb"
        if not original_name.lower().endswith(".afb"):
            flash("Attack Flow uploads must use the .afb extension.", "error")
            return redirect(url_for("assessment_detail", assessment_id=assessment_id))
        raw = uploaded.read()
        try:
            parsed = parse_attack_flow(raw)
        except AttackFlowError as exc:
            flash(str(exc), "error")
            return redirect(url_for("assessment_detail", assessment_id=assessment_id))
        sequence = next_sequence(assessment.attack_flows, "AFB")
        fari_id = f"AFB-{assessment_id:04d}-{sequence:03d}"
        stored_name = f"{fari_id}-{original_name}"
        target = Path(app.config["ATTACK_FLOW_DIR"]) / assessment.fari_id / stored_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        attack_flow = AttackFlow(
            assessment=assessment,
            fari_id=fari_id,
            filename=original_name,
            stored_name=stored_name,
            name=parsed["name"],
            description=parsed["description"],
            parsed_json=json.dumps(parsed),
        )
        db.session.add(attack_flow)
        touch_assessment(assessment)
        db.session.commit()
        flash(f"Attack Flow {fari_id} imported for read-only visualization.", "success")
        return redirect(url_for("attack_flow_detail", attack_flow_id=attack_flow.id))

    @app.post("/attack-flows/<int:attack_flow_id>/delete")
    def delete_attack_flow(attack_flow_id):
        attack_flow = get_record(AttackFlow, attack_flow_id)
        assessment = attack_flow.assessment
        ensure_assessment_open(assessment)
        assessment_id = assessment.id
        fari_id = attack_flow.fari_id
        target = (
            Path(app.config["ATTACK_FLOW_DIR"])
            / assessment.fari_id
            / attack_flow.stored_name
        )
        if target.exists():
            target.unlink()
        db.session.delete(attack_flow)
        touch_assessment(assessment)
        db.session.commit()
        flash(f"Attack Flow {fari_id} deleted.", "success")
        return redirect(url_for("assessment_detail", assessment_id=assessment_id))

    @app.get("/attack-flows/<int:attack_flow_id>")
    def attack_flow_detail(attack_flow_id):
        attack_flow = get_record(AttackFlow, attack_flow_id)
        graph = json.loads(attack_flow.parsed_json)
        if "groups" not in graph:
            source = (
                Path(app.config["ATTACK_FLOW_DIR"])
                / attack_flow.assessment.fari_id
                / attack_flow.stored_name
            )
            if source.exists():
                graph = parse_attack_flow(source.read_bytes())
        nodes_by_id = {node["id"]: node for node in graph["nodes"]}
        return render_template(
            "attack_flow_detail.html",
            attack_flow=attack_flow,
            assessment=attack_flow.assessment,
            graph=graph,
            nodes_by_id=nodes_by_id,
            phases=assessment_phases(attack_flow.assessment),
        )

    @app.post("/assessments/<int:assessment_id>/sbom")
    def upload_sbom(assessment_id):
        assessment = get_assessment(assessment_id)
        ensure_assessment_open(assessment)
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            flash("Select an SBOM or dependency inventory file.", "error")
            return redirect(url_for("assessment_detail", assessment_id=assessment_id))
        original_name = secure_filename(uploaded.filename) or "inventory.json"
        raw = uploaded.read()
        try:
            parsed = parse_sbom_bytes(original_name, raw)
        except (ValueError, json.JSONDecodeError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("assessment_detail", assessment_id=assessment_id))

        sequence = next_sequence(assessment.sbom_documents, "SBM")
        fari_id = f"SBM-{assessment_id:04d}-{sequence:03d}"
        stored_name = f"{fari_id}-{original_name}"
        target = sbom_path(assessment, stored_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        document = SbomDocument(
            assessment=assessment,
            asset_id=_integer_or_none(request.form.get("asset_id")),
            fari_id=fari_id,
            filename=original_name,
            stored_name=stored_name,
            file_format=parsed["format"],
            component_count=len(parsed["components"]),
            sha256=hashlib.sha256(raw).hexdigest(),
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(document)
        db.session.flush()

        imported = 0
        updated = 0
        for component_data in parsed["components"]:
            event_type = upsert_inventory_component(
                assessment,
                document,
                component_data,
                document.asset_id,
            )
            if event_type == "imported":
                imported += 1
            elif event_type == "version_updated":
                updated += 1

        touch_assessment(assessment)
        db.session.commit()
        flash(
            f"SBOM {document.fari_id} ingested. {imported} components added, {updated} versions changed.",
            "success",
        )
        return redirect(url_for("assessment_detail", assessment_id=assessment_id))

    @app.get("/sbom-documents/<int:document_id>/download")
    def download_sbom(document_id):
        document = get_record(SbomDocument, document_id)
        path = sbom_path(document.assessment, document.stored_name)
        if not path.exists():
            abort(404)
        return send_file(path, as_attachment=True, download_name=document.filename)

    @app.get("/inventory/components/<int:component_id>")
    def inventory_component_detail(component_id):
        component = get_record(InventoryComponent, component_id)
        return render_template(
            "inventory_component_detail.html",
            component=component,
            assessment=component.assessment,
            asset=component.asset,
            phases=assessment_phases(component.assessment),
        )

    @app.post("/inventory/components/<int:component_id>/events")
    def add_inventory_event(component_id):
        component = get_record(InventoryComponent, component_id)
        ensure_assessment_open(component.assessment)
        event_type = request.form.get("event_type", "note").strip() or "note"
        occurred_at = request.form.get("occurred_at", "").strip() or now_iso()
        to_version = request.form.get("to_version", "").strip()
        status_after = request.form.get("status_after", "").strip() or component.status
        sequence = next_sequence(component.events, "SBE")
        event = InventoryEvent(
            component=component,
            fari_id=f"SBE-{component_id:04d}-{sequence:03d}",
            event_type=event_type,
            occurred_at=occurred_at,
            from_version=request.form.get("from_version", "").strip(),
            to_version=to_version,
            vulnerability_id=request.form.get("vulnerability_id", "").strip(),
            severity=request.form.get("severity", "").strip(),
            summary=request.form.get("summary", "").strip(),
            status_after=status_after,
        )
        component.status = status_after
        if to_version:
            component.current_version = to_version
        component.notes = request.form.get("component_notes", "").strip()
        component.last_seen_at = occurred_at
        db.session.add(event)
        touch_assessment(component.assessment)
        db.session.commit()
        flash(f"Inventory event {event.fari_id} recorded.", "success")
        return redirect(url_for("inventory_component_detail", component_id=component_id))

    @app.get("/help/search")
    def help_search():
        return jsonify({"items": search_definitions(request.args.get("q", ""))})

    @app.get("/sparta/ttps")
    def sparta_ttps():
        try:
            catalog = load_sparta_catalog()
            return jsonify(
                {
                    "items": search_ttps(request.args.get("q", "")),
                    "version": catalog["version"],
                }
            )
        except (OSError, json.JSONDecodeError) as exc:
            return jsonify({"items": [], "error": str(exc)}), 503

    @app.get("/sparta/ttps/<path:ttp_id>/countermeasures")
    def sparta_countermeasures(ttp_id):
        try:
            return jsonify({"items": countermeasures_for(ttp_id)})
        except (OSError, json.JSONDecodeError) as exc:
            return jsonify({"items": [], "error": str(exc)}), 503

    @app.get("/investigations/<int:investigation_id>/report.docx")
    def investigation_report(investigation_id):
        investigation = get_investigation(investigation_id)
        output = build_investigation_report(
            investigation.assessment,
            investigation,
            investigation.asset,
            investigation.evidence,
            investigation.findings,
        )
        return send_file(
            output,
            as_attachment=True,
            download_name=(
                f"{investigation.fari_id}-Final-Investigation-Report.docx"
                if investigation.status == "closed"
                else f"{investigation.fari_id}-DRAFT-Investigation-Report.docx"
            ),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @app.get("/investigations/<int:investigation_id>/report.pdf")
    def investigation_report_pdf(investigation_id):
        investigation = get_investigation(investigation_id)
        if investigation.status != "closed":
            abort(409, description="PDF is available only after the investigation is closed.")
        output = build_investigation_pdf(
            investigation.assessment,
            investigation,
            investigation.asset,
            investigation.evidence,
            investigation.findings,
        )
        return send_file(
            output,
            as_attachment=True,
            download_name=f"{investigation.fari_id}-Final-Investigation-Report.pdf",
            mimetype="application/pdf",
        )

    @app.get("/assessments/<int:assessment_id>/consolidated.docx")
    def consolidated_report(assessment_id):
        assessment = get_assessment(assessment_id)
        output = build_consolidated_report(
            assessment, assessment.assets, assessment.investigations
        )
        return send_file(
            output,
            as_attachment=True,
            download_name=(
                f"{assessment.fari_id}-Final-Consolidated-Assessment.docx"
                if assessment.status == "closed"
                else f"{assessment.fari_id}-DRAFT-Consolidated-Assessment.docx"
            ),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @app.get("/assessments/<int:assessment_id>/consolidated.pdf")
    def consolidated_report_pdf(assessment_id):
        assessment = get_assessment(assessment_id)
        if assessment.status != "closed":
            abort(409, description="Consolidated PDF is available only after closure.")
        output = build_consolidated_pdf(
            assessment, assessment.assets, assessment.investigations
        )
        return send_file(
            output,
            as_attachment=True,
            download_name=f"{assessment.fari_id}-Final-Consolidated-Assessment.pdf",
            mimetype="application/pdf",
        )

    @app.get("/assessments/<int:assessment_id>/export.json")
    def export_assessment(assessment_id):
        assessment = get_assessment(assessment_id)
        investigations = []
        for item in assessment.investigations:
            exported = item.to_dict()
            exported["evidence"] = [record.to_dict() for record in item.evidence]
            exported["findings"] = [record.to_dict() for record in item.findings]
            investigations.append(exported)
        inventory = []
        for component in assessment.inventory_components:
            exported = component.to_dict()
            exported["events"] = [record.to_dict() for record in component.events]
            inventory.append(exported)
        compliance_profiles = []
        for profile in assessment.compliance_profiles:
            exported = profile.to_dict()
            exported["checks"] = [record.to_dict() for record in profile.checks]
            compliance_profiles.append(exported)
        payload = {
            "assessment": assessment.to_dict(),
            "assets": [item.to_dict() for item in assessment.assets],
            "investigations": investigations,
            "attack_flows": [item.to_dict() for item in assessment.attack_flows],
            "versions": [
                {**item.to_dict(), "snapshot": parse_version_snapshot(item)}
                for item in assessment.versions
            ],
            "sbom_documents": [item.to_dict() for item in assessment.sbom_documents],
            "inventory_components": inventory,
            "compliance_profiles": compliance_profiles,
            "overall_conclusion": overall_conclusion(assessment.investigations),
            "generated_with": FARI_GENERATED_WITH,
        }
        output = BytesIO(json.dumps(payload, indent=2).encode("utf-8"))
        return send_file(
            output,
            as_attachment=True,
            download_name=f"{assessment.fari_id}.json",
            mimetype="application/json",
        )

    def get_record(model, record_id):
        record = db.session.get(model, record_id)
        if record is None:
            abort(404)
        return record

    def get_assessment(assessment_id):
        return get_record(Assessment, assessment_id)

    def get_investigation(investigation_id):
        return get_record(Investigation, investigation_id)

    def evidence_path(investigation, stored_name):
        return Path(app.config["UPLOAD_DIR"]) / investigation.fari_id / stored_name

    def sbom_path(assessment, stored_name):
        return Path(app.config["SBOM_DIR"]) / assessment.fari_id / stored_name

    def ensure_assessment_open(assessment):
        if assessment.status == "closed":
            abort(409, description="This assessment is closed and immutable.")

    def ensure_investigation_open(investigation):
        if investigation.status == "closed" or investigation.assessment.status == "closed":
            abort(409, description="This investigation is closed and immutable.")

    return app


def _integer_or_none(value):
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def finding_values(form) -> dict:
    return {
        **{field: form.get(field, "").strip() for field in FINDING_FIELDS},
        "include_sparta_countermeasures": bool(
            form.get("include_sparta_countermeasures")
        ),
    }


def validate_investigation_form(form) -> str | None:
    if not form.get("title", "").strip() or not form.get("claim_description", "").strip():
        return "Investigation title and claim description are required."
    conclusion = form.get("conclusion", "not_assessed")
    required_action = form.get("required_action", "extend_investigation")
    if conclusion in {"meets", "does_not_meet"} and (
        not form.get("rationale", "").strip() or not form.get("scope_boundary", "").strip()
    ):
        return "Resolved conclusions require a rationale and scope boundary."
    if not result_action_valid(conclusion, required_action):
        if conclusion == "meets" and required_action == "remediate":
            return (
                "Meets cannot require Remediate. Rewrite the expected-behavior "
                "claim or select Does Not Meet."
            )
        return f"{human(conclusion)} is not compatible with {human(required_action)}."
    return None


def investigation_checks(investigation: Investigation) -> list[dict]:
    source_material = bool(
        investigation.evidence or investigation.facts.strip() or investigation.assertions.strip()
    )
    action_valid = result_action_valid(
        investigation.conclusion, investigation.required_action
    )
    return [
        {"label": "claim and scope", "done": bool(investigation.claim_description.strip() and investigation.scope_boundary.strip())},
        {"label": "technical reporter and method", "done": bool(investigation.technical_reporter.strip() and investigation.method.strip())},
        {"label": "evidence or normalized source material", "done": source_material},
        {"label": "resolved Result Card", "done": bool(investigation.conclusion != "not_assessed" and investigation.rationale.strip())},
        {"label": "scenario disposition selected", "done": investigation.scenario_state != "not_evaluated"},
        {"label": "valid required action", "done": action_valid},
    ]


def assessment_checks(assessment: Assessment) -> list[dict]:
    gating = [item for item in assessment.investigations if item.gating]
    return [
        {"label": "defined scope", "done": bool(assessment.scope.strip())},
        {"label": "at least one registered asset", "done": bool(assessment.assets)},
        {"label": "at least one gating investigation", "done": bool(gating)},
        {"label": "all gating investigations closed", "done": bool(gating) and all(item.status == "closed" for item in gating)},
    ]


def result_action_valid(conclusion: str, required_action: str) -> bool:
    valid = {
        "meets": {"accept", "no_action", "extend_investigation", "retest"},
        "does_not_meet": {"remediate", "extend_investigation", "retest"},
        "inconclusive": {"extend_investigation", "retest"},
        "not_assessed": {"extend_investigation", "no_action"},
    }
    return required_action in valid.get(conclusion, set())


def default_traceability_refs(assessment: Assessment, versions: list[AssessmentVersion]) -> tuple[str, str]:
    if assessment.status != "closed":
        return (str(versions[0].id), "current") if versions else ("current", "current")
    if len(versions) >= 2:
        return str(versions[1].id), str(versions[0].id)
    if len(versions) == 1:
        return str(versions[0].id), "current"
    return "current", "current"


def resolve_snapshot_ref(
    assessment: Assessment, versions: list[AssessmentVersion], ref: str | None
) -> dict | None:
    if ref == "current":
        return current_snapshot_reference(assessment)
    if not ref:
        return None
    for version in versions:
        if str(version.id) == str(ref):
            return {
                "id": str(version.id),
                "label": version.label,
                "summary": version.summary,
                "created_at": version.created_at,
                "trigger": version.trigger,
                "fari_id": version.fari_id,
                "snapshot": parse_version_snapshot(version),
            }
    return None


def find_inventory_component(
    assessment: Assessment, asset_id: int | None, name: str, ecosystem: str
) -> InventoryComponent | None:
    target_name = name.strip().lower()
    target_ecosystem = ecosystem.strip().lower() or "generic"
    for component in assessment.inventory_components:
        if (
            component.asset_id == asset_id
            and component.name.strip().lower() == target_name
            and component.ecosystem.strip().lower() == target_ecosystem
        ):
            return component
    return None


def upsert_inventory_component(
    assessment: Assessment,
    document: SbomDocument,
    component_data: dict,
    asset_id: int | None,
) -> str:
    component = find_inventory_component(
        assessment,
        asset_id,
        component_data.get("name", ""),
        component_data.get("ecosystem", "generic"),
    )
    event_type = ""
    if component is None:
        sequence = next_sequence(assessment.inventory_components, "CMP")
        component = InventoryComponent(
            assessment=assessment,
            asset_id=asset_id,
            latest_document=document,
            fari_id=f"CMP-{assessment.id:04d}-{sequence:03d}",
            name=component_data.get("name", "").strip(),
            ecosystem=component_data.get("ecosystem", "generic").strip() or "generic",
            current_version=component_data.get("version", "").strip(),
            purl=component_data.get("purl", "").strip(),
            component_type=component_data.get("component_type", "").strip(),
            license_name=component_data.get("license_name", "").strip(),
            status="tracked",
            first_seen_at=document.uploaded_at,
            last_seen_at=document.uploaded_at,
        )
        db.session.add(component)
        db.session.flush()
        event_type = "imported"
        db.session.add(
            InventoryEvent(
                component=component,
                document=document,
                fari_id=f"SBE-{component.id:04d}-001",
                event_type=event_type,
                occurred_at=document.uploaded_at,
                to_version=component.current_version,
                summary=f"Component imported from {document.fari_id}.",
                status_after=component.status,
            )
        )
        return event_type

    previous_version = component.current_version
    component.latest_document = document
    component.last_seen_at = document.uploaded_at
    component.purl = component_data.get("purl", "").strip()
    component.component_type = component_data.get("component_type", "").strip()
    component.license_name = component_data.get("license_name", "").strip()
    new_version = component_data.get("version", "").strip()
    if new_version and new_version != previous_version:
        component.current_version = new_version
        sequence = next_sequence(component.events, "SBE")
        event_type = "version_updated"
        db.session.add(
            InventoryEvent(
                component=component,
                document=document,
                fari_id=f"SBE-{component.id:04d}-{sequence:03d}",
                event_type=event_type,
                occurred_at=document.uploaded_at,
                from_version=previous_version,
                to_version=new_version,
                summary=f"SBOM refresh {document.fari_id} updated the recorded component version.",
                status_after=component.status,
            )
        )
    return event_type


def build_assessment_summaries(assessments: list[Assessment]) -> list[dict]:
    summaries = []
    for assessment in assessments:
        result = overall_conclusion(assessment.investigations)
        summaries.append(
            {
                "assessment": assessment,
                "result": result,
                "asset_count": len(assessment.assets),
                "investigation_count": len(assessment.investigations),
                "closed_count": sum(
                    item.status == "closed" for item in assessment.investigations
                ),
                "open_count": sum(
                    item.status != "closed" for item in assessment.investigations
                ),
                "updated_at": assessment.updated_at,
                "revision_label": latest_revision_label(assessment),
            }
        )
    return summaries


def assessment_phases(assessment: Assessment) -> list[dict]:
    investigations = list(assessment.investigations)
    acquired = bool(investigations) and all(
        item.evidence or item.facts.strip() or item.assertions.strip()
        for item in investigations
    )
    related = bool(investigations) and all(
        item.conclusion != "not_assessed" and item.rationale.strip()
        for item in investigations
    )
    base = url_for("assessment_detail", assessment_id=assessment.id)
    steps = [
        ("01", "Frame", "Client, scope, assets, and claims", bool(assessment.scope.strip() and assessment.assets), f"{base}#frame"),
        ("02", "Acquire", "Evidence, inventory, and sufficiency", acquired, f"{base}#acquire"),
        ("03", "Relate", "Findings, SBOM state, scenarios, and SPARTA", related, f"{base}#relate"),
        ("04", "Inform", "Close and publish consolidated reports", assessment.status == "closed", f"{base}#inform"),
    ]
    current_found = False
    phases = []
    for number, name, copy, done, href in steps:
        if done:
            state = "complete"
        elif not current_found:
            state = "current"
            current_found = True
        else:
            state = "pending"
        phases.append(
            {"number": number, "name": name, "detail": copy, "state": state, "href": href}
        )
    return phases


def new_assessment_phases() -> list[dict]:
    return [
        {"number": "01", "name": "Frame", "detail": "Client, scope, assets, and claims", "state": "current", "href": "#frame"},
        {"number": "02", "name": "Acquire", "detail": "Evidence, inventory, and sufficiency", "state": "pending", "href": "#"},
        {"number": "03", "name": "Relate", "detail": "Findings, SBOM state, scenarios, and SPARTA", "state": "pending", "href": "#"},
        {"number": "04", "name": "Inform", "detail": "Close and publish consolidated reports", "state": "pending", "href": "#"},
    ]


def touch_assessment(assessment: Assessment) -> None:
    assessment.updated_at = now_iso()


def touch_investigation(investigation: Investigation) -> None:
    investigation.updated_at = now_iso()
    touch_assessment(investigation.assessment)


app = create_app()
