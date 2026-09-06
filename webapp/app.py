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
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from werkzeug.utils import secure_filename

from webapp.i18n import TranslationCatalog, load_catalog
from webapp.db import (
    Assessment,
    AssessmentVersion,
    Asset,
    Evidence,
    Finding,
    InventoryComponent,
    InventoryEvent,
    Investigation,
    AssetSource,
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
from webapp.asset_sources import parse_asset_source
from webapp.contract import CONCLUSION_ACTIONS, CONTRACT
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
login_manager.login_message = None
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
        ASSET_SOURCE_DIR=str(data_dir / "sources"),
        FARI_LOGIN_USERNAME=os.environ.get("FARI_LOGIN_USERNAME", "fari"),
        FARI_LOGIN_PASSWORD=os.environ.get("FARI_LOGIN_PASSWORD", "toor"),
        FARI_REPOSITORY_URL=os.environ.get("FARI_REPOSITORY_URL", ""),
        FARI_BRAND_IMAGE_URL=os.environ.get("FARI_BRAND_IMAGE_URL", ""),
        FARI_DEFAULT_LANGUAGE=os.environ.get("FARI_DEFAULT_LANGUAGE", "en"),
        FARI_TRANSLATIONS_DIR=str(PROJECT_ROOT / "webapp" / "translations"),
        MAX_CONTENT_LENGTH=int(os.environ.get("FARI_MAX_UPLOAD_MB", "250")) * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
        database_parent = Path(app.config["DATABASE"]).parent
        if "ASSET_SOURCE_DIR" not in test_config:
            app.config["ASSET_SOURCE_DIR"] = str(database_parent / "sources")
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
    Path(app.config["ASSET_SOURCE_DIR"]).mkdir(parents=True, exist_ok=True)
    catalog: TranslationCatalog = load_catalog(app.config["FARI_TRANSLATIONS_DIR"])
    app.config["FARI_DEFAULT_LANGUAGE"] = catalog.normalize(
        app.config["FARI_DEFAULT_LANGUAGE"]
    )
    init_db(app)
    login_manager.init_app(app)

    def language() -> str:
        return catalog.normalize(session.get("language", app.config["FARI_DEFAULT_LANGUAGE"]))

    def translate(key: str, **values):
        return catalog.get(key, language(), **values)

    app.jinja_env.filters["human"] = lambda value: catalog.human(value, language())
    app.jinja_env.globals["_"] = translate
    app.jinja_env.globals["fari_language"] = language
    app.jinja_env.globals["fari_language_options"] = catalog.language_options()
    app.jinja_env.globals["fari_generated_with"] = FARI_GENERATED_WITH
    app.jinja_env.globals["fari_version"] = FARI_VERSION
    app.jinja_env.globals["fari_repository_url"] = app.config["FARI_REPOSITORY_URL"]
    app.jinja_env.globals["fari_brand_image_url"] = app.config["FARI_BRAND_IMAGE_URL"]
    app.jinja_env.globals["format_bytes"] = format_bytes
    app.jinja_env.globals["fari_contract"] = CONTRACT
    app.jinja_env.globals["form_value"] = lambda name, default="": (
        request.form.get(name, default) if request.method == "POST" else default
    )
    app.jinja_env.globals["form_checked"] = lambda name, default=False: (
        name in request.form if request.method == "POST" else default
    )

    @app.before_request
    def set_language_context():
        g.fari_catalog = catalog
        g.fari_language = language()
        return None

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
            "label_key": "resource.specification.label",
            "description_key": "resource.specification.description",
            "path": release_file("specification", f"FARI-Specification-v{FARI_VERSION}.pdf"),
            "download_name": f"FARI-Specification-v{FARI_VERSION}.pdf",
        },
        {
            "slug": "manual-template",
            "label_key": "resource.manual.label",
            "description_key": "resource.manual.description",
            "path": release_file("manual-template", f"FARI-Manual-Template-v{FARI_VERSION}.pdf"),
            "download_name": f"FARI-Manual-Template-v{FARI_VERSION}.pdf",
        },
        {
            "slug": "scenario-catalog",
            "label_key": "resource.catalog.label",
            "description_key": "resource.catalog.description",
            "path": release_file("reports", f"FARI-SCENARIO-TEST_CATALOG-v{FARI_VERSION}.pdf"),
            "download_name": f"FARI-SCENARIO-TEST_CATALOG-v{FARI_VERSION}.pdf",
        },
        {
            "slug": "schema",
            "label_key": "resource.schema.label",
            "description_key": "resource.schema.description",
            "path": SPEC_SCHEMA_ROOT / "fari-assessment.schema.json",
            "download_name": "fari-assessment.schema.json",
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

    @app.get("/language")
    def set_language():
        selected = catalog.normalize(request.args.get("language"))
        session["language"] = selected
        return redirect(safe_redirect_target(request.args.get("next")))

    @app.get("/language/dictionary")
    def language_dictionary():
        return render_template(
            "language_dictionary.html",
            dictionary=catalog.review(language()),
            exceptions=catalog.exceptions,
        )

    @login_manager.unauthorized_handler
    def unauthorized():
        flash(translate("auth.sign_in_to_continue"), "error")
        return redirect(url_for("login", next=request.full_path if request.query_string else request.path))

    @app.before_request
    def require_workspace_login():
        endpoint = request.endpoint or ""
        if endpoint in {"login", "static", "set_language"}:
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
                flash(translate("flash.workspace_granted"), "success")
                return redirect(safe_redirect_target(next_target))
            flash(translate("flash.invalid_credentials"), "error")
        return render_template("login.html", next_target=safe_redirect_target(next_target))

    @app.post("/logout")
    def logout():
        logout_user()
        flash(translate("flash.signed_out"), "success")
        return redirect(url_for("login"))

    @app.get("/")
    def index():
        status_filter = request.args.get("status", "all").strip().lower()
        result_filter = request.args.get("result", "all").strip().lower()
        limit = _integer_or_none(request.args.get("limit")) or 25
        if status_filter not in {"all", *CONTRACT["assessment_statuses"]}:
            status_filter = "all"
        if result_filter not in {"all", *CONTRACT["conclusions"]}:
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
        return render_template(
            "assessment_detail.html",
            assessment=assessment,
            assets=assessment.assets,
            investigations=assessment.investigations,
            asset_source_count=sum(len(asset.sources) for asset in assessment.assets),
            asset_component_count=sum(
                len(asset.inventory_components) for asset in assessment.assets
            ),
            overall=overall_conclusion(assessment.investigations),
            checks=checks,
            phases=assessment_phases(assessment),
            revision_label=latest_revision_label(assessment),
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
        source_root = Path(app.config["ASSET_SOURCE_DIR"]) / assessment.fari_id
        db.session.delete(assessment)
        db.session.commit()
        for investigation_id in investigation_ids:
            shutil.rmtree(Path(app.config["UPLOAD_DIR"]) / investigation_id, ignore_errors=True)
        shutil.rmtree(source_root, ignore_errors=True)
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

    @app.get("/assets/<int:asset_id>")
    def asset_detail(asset_id):
        asset = get_record(Asset, asset_id)
        assessment = asset.assessment
        return render_template(
            "asset_detail.html",
            asset=asset,
            assessment=assessment,
            sources=asset.sources,
            inventory_components=asset.inventory_components,
            investigations=asset.investigations,
            phases=assessment_phases(assessment),
        )

    @app.post("/assets/<int:asset_id>/delete")
    def delete_asset(asset_id):
        asset = get_record(Asset, asset_id)
        assessment = asset.assessment
        ensure_assessment_open(assessment)
        assessment_id = assessment.id
        fari_id = asset.fari_id
        for investigation in list(asset.investigations):
            investigation.asset_id = None
        for source in list(asset.sources):
            source.asset_id = None
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
                flash(f"Finding {finding.fari_id} was updated.", "success")
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

    @app.post("/assets/<int:asset_id>/sources")
    def upload_asset_source(asset_id):
        asset = get_record(Asset, asset_id)
        assessment = asset.assessment
        ensure_assessment_open(assessment)
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            flash(translate("flash.select_asset_source"), "error")
            return redirect(url_for("asset_detail", asset_id=asset_id))
        original_name = secure_filename(uploaded.filename) or "asset-source.bin"
        raw = uploaded.read()
        try:
            parsed = parse_asset_source(original_name, raw)
        except (ValueError, json.JSONDecodeError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("asset_detail", asset_id=asset_id))

        sequence = next_sequence(asset.sources, "SRC")
        fari_id = f"SRC-{assessment.id:04d}-{sequence:03d}"
        stored_name = f"{fari_id}-{original_name}"
        target = asset_source_path(asset, stored_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        document = AssetSource(
            assessment=assessment,
            asset=asset,
            fari_id=fari_id,
            filename=original_name,
            stored_name=stored_name,
            file_format=parsed["format"],
            component_count=len(parsed["components"]),
            sha256=hashlib.sha256(raw).hexdigest(),
            byte_size=len(raw),
            mime_type=uploaded.mimetype or "application/octet-stream",
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
                asset.id,
            )
            if event_type == "imported":
                imported += 1
            elif event_type == "version_updated":
                updated += 1

        touch_assessment(assessment)
        db.session.commit()
        flash(
            translate(
                "flash.asset_source_summary",
                id=document.fari_id,
                imported=imported,
                updated=updated,
            ),
            "success",
        )
        return redirect(url_for("asset_detail", asset_id=asset_id))

    @app.get("/asset-sources/<int:source_id>/download")
    def download_asset_source(source_id):
        document = get_record(AssetSource, source_id)
        if not document.asset:
            abort(404)
        path = asset_source_path(document.asset, document.stored_name)
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

    @app.get("/investigations/<int:investigation_id>/report.docx")
    def investigation_report(investigation_id):
        investigation = get_investigation(investigation_id)
        output = build_investigation_report(
            investigation.assessment,
            investigation,
            investigation.asset,
            investigation.evidence,
            investigation.findings,
            language=language(),
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
            language=language(),
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
            assessment, assessment.assets, assessment.investigations, language=language()
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
            assessment, assessment.assets, assessment.investigations, language=language()
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
        payload = build_export_payload(assessment)
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

    def asset_source_path(asset, stored_name):
        return (
            Path(app.config["ASSET_SOURCE_DIR"])
            / asset.assessment.fari_id
            / asset.fari_id
            / stored_name
        )

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


def format_bytes(value: int | None) -> str:
    amount = max(int(value or 0), 0)
    units = ("B", "KB", "MB", "GB")
    size = float(amount)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{amount} B"
        size /= 1024
    return f"{amount} B"


def _date_only(value: str) -> str:
    return (value or "")[:10]


def _lines(value: str) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _asset_source_material(source: AssetSource) -> dict:
    asset = source.asset
    asset_label = asset.fari_id if asset else "unassigned"
    return {
        "id": source.fari_id,
        "description": source.notes or f"Technical source file {source.filename} for {asset_label}.",
        "source": asset_label,
        "received_date": _date_only(source.uploaded_at),
        "original_format": source.file_format,
        "controlled_reference": f"asset-sources/{asset_label}/{source.stored_name}",
        "integrity": f"sha256:{source.sha256}",
        "limitations": [],
    }


def _evidence_source_material(evidence: Evidence) -> dict:
    source_id = f"SRC-{evidence.fari_id}"
    return {
        "id": source_id,
        "description": evidence.description or f"Evidence file {evidence.filename}.",
        "source": "web workspace upload",
        "received_date": _date_only(evidence.uploaded_at),
        "original_format": evidence.mime_type or "unknown",
        "controlled_reference": f"evidence/{evidence.investigation.fari_id}/{evidence.stored_name}",
        "integrity": f"sha256:{evidence.sha256}",
        "limitations": [],
    }


def _canonical_asset(asset: Asset) -> dict:
    return {
        "id": asset.fari_id,
        "fari_id": asset.fari_id,
        "name": asset.name,
        "segment": asset.segment,
        "access_model": asset.access_model,
        "coverage": asset.coverage,
        "description": asset.description or "",
        "mission_objectives": [],
    }


def _canonical_finding(finding: Finding, investigation: Investigation) -> dict:
    asset_ids = [investigation.asset.fari_id] if investigation.asset else []
    evidence_ids = [item.fari_id for item in investigation.evidence]
    return {
        "id": finding.fari_id,
        "title": finding.title,
        "state": finding.state,
        "asset_ids": asset_ids,
        "evidence_ids": evidence_ids,
        "confidence": investigation.confidence,
        "fari_conclusion": investigation.conclusion,
        "required_action": investigation.required_action,
        "condition_text": finding.condition_text,
        "observed_effect": finding.observed_effect,
        "credible_impact": finding.credible_impact,
        "mapping_state": finding.mapping_state,
        "mapping_rationale": finding.mapping_rationale,
        "mappings": [],
        "limitations": _lines(investigation.gaps),
    }


def _canonical_inventory_event(event: InventoryEvent) -> dict:
    return {
        "fari_id": event.fari_id,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "from_version": event.from_version or "",
        "to_version": event.to_version or "",
        "vulnerability_id": event.vulnerability_id or "",
        "severity": event.severity or "",
        "summary": event.summary or "",
        "status_after": event.status_after or "",
    }


def _investigation_source_ids(investigation: Investigation) -> list[str]:
    ids = []
    if investigation.asset:
        ids.extend(source.fari_id for source in investigation.asset.sources)
    ids.extend(f"SRC-{item.fari_id}" for item in investigation.evidence)
    return list(dict.fromkeys(ids))


def build_export_payload(assessment: Assessment) -> dict:
    """Build the normalized bundle described by the current FARI schema."""

    assets = [_canonical_asset(asset) for asset in assessment.assets]
    claims = []
    source_materials = []
    investigations = []
    method_runs = []
    evidence = []
    evidence_reviews = []
    findings = []
    conclusions = []
    assurance = []

    for source in assessment.asset_sources:
        source_materials.append(_asset_source_material(source))

    for investigation in assessment.investigations:
        claim_id = investigation.claim_id
        asset_ids = [investigation.asset.fari_id] if investigation.asset else []
        source_ids = _investigation_source_ids(investigation)
        run_id = f"RUN-{investigation.fari_id}"
        conclusion_id = f"CON-{investigation.fari_id}"
        claims.append(
            {
                "id": claim_id,
                "statement": investigation.claim_description,
                "gating": investigation.gating,
                "conclusion": investigation.conclusion,
                "asset_ids": asset_ids,
            }
        )

        for item in investigation.evidence:
            source_materials.append(_evidence_source_material(item))
            evidence.append(
                {
                    "id": item.fari_id,
                    "description": item.description or item.filename,
                    "method_run_id": run_id,
                    "source_material_id": f"SRC-{item.fari_id}",
                    "integrity": f"sha256:{item.sha256}",
                    "controlled_reference": f"evidence/{investigation.fari_id}/{item.stored_name}",
                }
            )

        canonical_findings = [
            _canonical_finding(item, investigation) for item in investigation.findings
        ]
        findings.extend(canonical_findings)
        investigations.append(
            {
                "id": investigation.fari_id,
                "fari_id": investigation.fari_id,
                "title": investigation.title,
                "claim_ids": [claim_id],
                "source_material_ids": source_ids,
                "finding_ids": [item["id"] for item in canonical_findings],
                "conclusion_id": conclusion_id,
                "report_reference": f"reports/{investigation.fari_id}",
                "method_run_id": run_id,
                "evidence": [item for item in evidence if item["method_run_id"] == run_id],
                "findings": canonical_findings,
            }
        )
        method_runs.append(
            {
                "id": run_id,
                "method": investigation.method,
                "environment": investigation.environment,
                "status": {
                    "draft": "planned",
                    "ready": "active",
                    "closed": "complete",
                }.get(investigation.status, "planned"),
                "source_material_ids": source_ids,
                "limitations": _lines(investigation.gaps),
            }
        )
        evidence_reviews.append(
            {
                "id": f"EIR-{investigation.fari_id}",
                "method_run_ids": [run_id],
                "source_material_ids": source_ids,
                "review_date": _date_only(investigation.updated_at),
                "technical_condition_sufficiency": investigation.technical_sufficiency,
                "reachability_sufficiency": investigation.reachability_sufficiency,
                "mission_consequence_sufficiency": investigation.mission_sufficiency,
                "evidence_backed_facts": _lines(investigation.facts),
                "producer_assertions": _lines(investigation.assertions),
                "report_author_inferences": _lines(investigation.inferences),
                "assumptions": _lines(investigation.assumptions),
                "contradictions": _lines(investigation.contradictions),
                "evidence_gaps": _lines(investigation.gaps),
            }
        )
        conclusions.append(
            {
                "id": conclusion_id,
                "level": "investigation",
                "value": investigation.conclusion,
                "scenario_disposition": investigation.scenario_state,
                "confidence": investigation.confidence,
                "required_action": investigation.required_action,
                "priority": investigation.priority,
                "scope_boundary": investigation.scope_boundary,
                "rationale": investigation.rationale,
                "gating_claim_ids": [claim_id] if investigation.gating else [],
            }
        )
        assurance.append(
            {
                "id": f"ASR-{investigation.fari_id}",
                "claim_id": claim_id,
                "conclusion": investigation.conclusion,
                "confidence": investigation.confidence,
                "limitations": _lines(investigation.gaps),
            }
        )

    overall = overall_conclusion(assessment.investigations)
    gating_investigations = [item for item in assessment.investigations if item.gating]
    overall_scenario = "not_evaluated"
    if any(item.scenario_state == "demonstrated" for item in gating_investigations):
        overall_scenario = "demonstrated"
    elif any(item.scenario_state == "plausible" for item in gating_investigations):
        overall_scenario = "plausible"
    elif any(item.scenario_state == "not_demonstrated" for item in gating_investigations):
        overall_scenario = "not_demonstrated"
    assessment_conclusion_id = f"CON-{assessment.fari_id}"
    conclusions.append(
        {
            "id": assessment_conclusion_id,
            "level": "assessment",
            "value": overall,
            "scenario_disposition": overall_scenario,
            "confidence": "medium" if assessment.investigations else "low",
            "required_action": {
                "meets": "accept",
                "does_not_meet": "remediate",
                "inconclusive": "extend_investigation",
                "not_assessed": "extend_investigation",
            }[overall],
            "priority": "immediate" if overall == "does_not_meet" else "planned",
            "scope_boundary": assessment.scope,
            "rationale": f"Derived from {sum(item.gating for item in assessment.investigations)} gating investigation(s).",
            "gating_claim_ids": [item.claim_id for item in assessment.investigations if item.gating],
            "aggregation_rule": "Does Not Meet when any gating investigation Does Not Meet; otherwise Inconclusive when any gating investigation is Inconclusive or Not Assessed; otherwise Meets.",
        }
    )

    inventory_components = []
    for component in assessment.inventory_components:
        inventory_components.append(
            {
                "fari_id": component.fari_id,
                "name": component.name,
                "ecosystem": component.ecosystem,
                "current_version": component.current_version,
                "status": component.status,
                "asset_id": component.asset.fari_id if component.asset else None,
                "purl": component.purl,
                "component_type": component.component_type,
                "license_name": component.license_name,
                "notes": component.notes,
                "first_seen_at": component.first_seen_at,
                "last_seen_at": component.last_seen_at,
                "events": [_canonical_inventory_event(item) for item in component.events],
            }
        )

    return {
        "assessment": {
            "id": assessment.fari_id,
            "title": assessment.title,
            "status": assessment.status,
            "report_maturity": assessment.maturity,
            "framework_profiles": [],
            "scope_summary": assessment.scope,
            "conclusion_id": assessment_conclusion_id,
            "roles": {"report_author": assessment.report_author},
            "limitations": _lines(assessment.exclusions),
        },
        "mission_objectives": [],
        "assets": assets,
        "claims": claims,
        "source_materials": source_materials,
        "investigations": investigations,
        "method_runs": method_runs,
        "evidence": evidence,
        "evidence_intake_reviews": evidence_reviews,
        "findings": findings,
        "versions": [
            {
                "fari_id": item.fari_id,
                "version_number": item.version_number,
                "label": item.label,
                "trigger": item.trigger,
                "summary": item.summary,
                "created_at": item.created_at,
                "snapshot": parse_version_snapshot(item),
            }
            for item in assessment.versions
        ],
        "asset_sources": [
            {
                "fari_id": item.fari_id,
                "filename": item.filename,
                "file_format": item.file_format,
                "component_count": item.component_count,
                "sha256": item.sha256,
                "byte_size": item.byte_size,
                "mime_type": item.mime_type,
                "asset_id": item.asset.fari_id if item.asset else None,
                "notes": item.notes,
                "uploaded_at": item.uploaded_at,
            }
            for item in assessment.asset_sources
        ],
        "inventory_components": inventory_components,
        "risks": [],
        "conclusions": conclusions,
        "assurance": assurance,
        "generated_with": FARI_GENERATED_WITH,
        "implementation": {
            "edition": "web",
            "database_id": assessment.id,
            "revision_count": assessment.revision_count,
            "languages": ["en", "es"],
        },
    }


def finding_values(form) -> dict:
    return {field: form.get(field, "").strip() for field in FINDING_FIELDS}


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
    return required_action in CONCLUSION_ACTIONS.get(conclusion, frozenset())


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
    document: AssetSource,
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
                summary=f"Asset source {document.fari_id} refreshed the recorded component version.",
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
        ("01", "phase.frame", "phase.frame_detail", bool(assessment.scope.strip() and assessment.assets), f"{base}#frame"),
        ("02", "phase.acquire", "phase.acquire_detail", acquired, f"{base}#acquire"),
        ("03", "phase.relate", "phase.relate_detail", related, f"{base}#relate"),
        ("04", "phase.inform", "phase.inform_detail", assessment.status == "closed", f"{base}#inform"),
    ]
    current_found = False
    phases = []
    for number, name_key, detail_key, done, href in steps:
        if done:
            state = "complete"
        elif not current_found:
            state = "current"
            current_found = True
        else:
            state = "pending"
        phases.append(
            {"number": number, "name_key": name_key, "detail_key": detail_key, "state": state, "href": href}
        )
    return phases


def new_assessment_phases() -> list[dict]:
    return [
        {"number": "01", "name_key": "phase.frame", "detail_key": "phase.frame_detail", "state": "current", "href": "#frame"},
        {"number": "02", "name_key": "phase.acquire", "detail_key": "phase.acquire_detail", "state": "pending", "href": "#"},
        {"number": "03", "name_key": "phase.relate", "detail_key": "phase.relate_detail", "state": "pending", "href": "#"},
        {"number": "04", "name_key": "phase.inform", "detail_key": "phase.inform_detail", "state": "pending", "href": "#"},
    ]


def touch_assessment(assessment: Assessment) -> None:
    assessment.updated_at = now_iso()


def touch_investigation(investigation: Investigation) -> None:
    investigation.updated_at = now_iso()
    touch_assessment(investigation.assessment)


app = create_app()
