"""SQLAlchemy models and persistence helpers for the FARI web application."""

from __future__ import annotations

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine


db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, _connection_record):
    """Keep SQLite cascades consistent with the declared model relationships."""
    if connection.__class__.__module__.split(".", 1)[0] != "sqlite3":
        return
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class RecordMixin:
    """Make ORM records compatible with existing report/template mapping access."""

    def __getitem__(self, key):
        return getattr(self, key)

    def to_dict(self) -> dict:
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Assessment(RecordMixin, db.Model):
    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    fari_id = db.Column(db.String, unique=True)
    client_name = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    mission_context = db.Column(db.Text, default="")
    scope = db.Column(db.Text, default="")
    authorization = db.Column(db.Text, default="")
    exclusions = db.Column(db.Text, default="")
    status = db.Column(db.String, nullable=False, default="draft")
    maturity = db.Column(db.String, nullable=False, default="provisional")
    revision_count = db.Column(db.Integer, nullable=False, default=0)
    report_author = db.Column(db.String, nullable=False, default="Fari-Agent")
    created_at = db.Column(db.String, nullable=False, default=now_iso)
    updated_at = db.Column(db.String, nullable=False, default=now_iso)

    assets = db.relationship(
        "Asset", back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )
    investigations = db.relationship(
        "Investigation",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    attack_flows = db.relationship(
        "AttackFlow",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    versions = db.relationship(
        "AssessmentVersion",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssessmentVersion.version_number",
    )
    sbom_documents = db.relationship(
        "SbomDocument",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SbomDocument.uploaded_at",
    )
    inventory_components = db.relationship(
        "InventoryComponent",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InventoryComponent.fari_id",
    )
    compliance_profiles = db.relationship(
        "ComplianceProfile",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ComplianceProfile.created_at",
    )


class Asset(RecordMixin, db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    fari_id = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    segment = db.Column(db.String, nullable=False, default="space")
    description = db.Column(db.Text, default="")
    access_model = db.Column(db.String, nullable=False, default="private")
    coverage = db.Column(db.String, nullable=False, default="not_assessed")
    created_at = db.Column(db.String, nullable=False, default=now_iso)

    assessment = db.relationship("Assessment", back_populates="assets")
    investigations = db.relationship("Investigation", back_populates="asset")
    sbom_documents = db.relationship("SbomDocument", back_populates="asset")
    inventory_components = db.relationship("InventoryComponent", back_populates="asset")


class AssessmentVersion(RecordMixin, db.Model):
    __tablename__ = "assessment_versions"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    fari_id = db.Column(db.String, nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String, nullable=False)
    trigger = db.Column(db.String, nullable=False, default="manual_snapshot")
    summary = db.Column(db.Text, default="")
    snapshot_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.String, nullable=False, default=now_iso)

    assessment = db.relationship("Assessment", back_populates="versions")


class Investigation(RecordMixin, db.Model):
    __tablename__ = "investigations"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id", ondelete="SET NULL"))
    fari_id = db.Column(db.String, nullable=False)
    claim_id = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    claim_description = db.Column(db.Text, nullable=False)
    gating = db.Column(db.Boolean, nullable=False, default=True)
    technical_reporter = db.Column(db.String, default="")
    method = db.Column(db.Text, default="")
    environment = db.Column(db.Text, default="")
    facts = db.Column(db.Text, default="")
    assertions = db.Column(db.Text, default="")
    inferences = db.Column(db.Text, default="")
    assumptions = db.Column(db.Text, default="")
    contradictions = db.Column(db.Text, default="")
    gaps = db.Column(db.Text, default="")
    technical_sufficiency = db.Column(db.String, nullable=False, default="insufficient")
    reachability_sufficiency = db.Column(db.String, nullable=False, default="insufficient")
    mission_sufficiency = db.Column(db.String, nullable=False, default="insufficient")
    conclusion = db.Column(db.String, nullable=False, default="not_assessed")
    scenario_state = db.Column(db.String, nullable=False, default="not_evaluated")
    confidence = db.Column(db.String, nullable=False, default="low")
    required_action = db.Column(db.String, nullable=False, default="extend_investigation")
    priority = db.Column(db.String, nullable=False, default="planned")
    scope_boundary = db.Column(db.Text, default="")
    rationale = db.Column(db.Text, default="")
    recommendations = db.Column(db.Text, default="")
    acceptance_criteria = db.Column(db.Text, default="")
    status = db.Column(db.String, nullable=False, default="draft")
    created_at = db.Column(db.String, nullable=False, default=now_iso)
    updated_at = db.Column(db.String, nullable=False, default=now_iso)

    assessment = db.relationship("Assessment", back_populates="investigations")
    asset = db.relationship("Asset", back_populates="investigations")
    evidence = db.relationship(
        "Evidence",
        back_populates="investigation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    findings = db.relationship(
        "Finding",
        back_populates="investigation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Evidence(RecordMixin, db.Model):
    __tablename__ = "evidence"

    id = db.Column(db.Integer, primary_key=True)
    investigation_id = db.Column(
        db.Integer, db.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    fari_id = db.Column(db.String, nullable=False)
    filename = db.Column(db.String, nullable=False)
    stored_name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, default="")
    sha256 = db.Column(db.String, nullable=False)
    mime_type = db.Column(db.String, default="")
    uploaded_at = db.Column(db.String, nullable=False, default=now_iso)

    investigation = db.relationship("Investigation", back_populates="evidence")


class Finding(RecordMixin, db.Model):
    __tablename__ = "findings"

    id = db.Column(db.Integer, primary_key=True)
    investigation_id = db.Column(
        db.Integer, db.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    fari_id = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    state = db.Column(db.String, nullable=False, default="candidate")
    condition_text = db.Column(db.Text, default="")
    observed_effect = db.Column(db.Text, default="")
    credible_impact = db.Column(db.Text, default="")
    sparta_id = db.Column(db.String, default="")
    sparta_name = db.Column(db.String, default="")
    mapping_state = db.Column(db.String, nullable=False, default="candidate")
    mapping_rationale = db.Column(db.Text, default="")
    include_sparta_countermeasures = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.String, nullable=False, default=now_iso)

    investigation = db.relationship("Investigation", back_populates="findings")


class AttackFlow(RecordMixin, db.Model):
    __tablename__ = "attack_flows"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    fari_id = db.Column(db.String, nullable=False)
    filename = db.Column(db.String, nullable=False)
    stored_name = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, default="")
    parsed_json = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.String, nullable=False, default=now_iso)

    assessment = db.relationship("Assessment", back_populates="attack_flows")


class SbomDocument(RecordMixin, db.Model):
    __tablename__ = "sbom_documents"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id", ondelete="SET NULL"))
    fari_id = db.Column(db.String, nullable=False)
    filename = db.Column(db.String, nullable=False)
    stored_name = db.Column(db.String, nullable=False)
    file_format = db.Column(db.String, nullable=False, default="unknown")
    component_count = db.Column(db.Integer, nullable=False, default=0)
    sha256 = db.Column(db.String, nullable=False)
    notes = db.Column(db.Text, default="")
    uploaded_at = db.Column(db.String, nullable=False, default=now_iso)

    assessment = db.relationship("Assessment", back_populates="sbom_documents")
    asset = db.relationship("Asset", back_populates="sbom_documents")
    inventory_events = db.relationship("InventoryEvent", back_populates="document")


class InventoryComponent(RecordMixin, db.Model):
    __tablename__ = "inventory_components"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id", ondelete="SET NULL"))
    latest_document_id = db.Column(
        db.Integer, db.ForeignKey("sbom_documents.id", ondelete="SET NULL")
    )
    fari_id = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    ecosystem = db.Column(db.String, nullable=False, default="generic")
    current_version = db.Column(db.String, nullable=False, default="")
    purl = db.Column(db.String, default="")
    component_type = db.Column(db.String, default="")
    license_name = db.Column(db.String, default="")
    status = db.Column(db.String, nullable=False, default="tracked")
    notes = db.Column(db.Text, default="")
    first_seen_at = db.Column(db.String, nullable=False, default=now_iso)
    last_seen_at = db.Column(db.String, nullable=False, default=now_iso)

    assessment = db.relationship("Assessment", back_populates="inventory_components")
    asset = db.relationship("Asset", back_populates="inventory_components")
    latest_document = db.relationship("SbomDocument")
    events = db.relationship(
        "InventoryEvent",
        back_populates="component",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InventoryEvent.occurred_at",
    )


class InventoryEvent(RecordMixin, db.Model):
    __tablename__ = "inventory_events"

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_components.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id = db.Column(db.Integer, db.ForeignKey("sbom_documents.id", ondelete="SET NULL"))
    fari_id = db.Column(db.String, nullable=False)
    event_type = db.Column(db.String, nullable=False, default="note")
    occurred_at = db.Column(db.String, nullable=False, default=now_iso)
    from_version = db.Column(db.String, default="")
    to_version = db.Column(db.String, default="")
    vulnerability_id = db.Column(db.String, default="")
    severity = db.Column(db.String, default="")
    summary = db.Column(db.Text, default="")
    status_after = db.Column(db.String, default="")
    created_at = db.Column(db.String, nullable=False, default=now_iso)

    component = db.relationship("InventoryComponent", back_populates="events")
    document = db.relationship("SbomDocument", back_populates="inventory_events")


class ComplianceProfile(RecordMixin, db.Model):
    __tablename__ = "compliance_profiles"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    fari_id = db.Column(db.String, nullable=False)
    profile_key = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    framework_name = db.Column(db.String, nullable=False, default="")
    framework_version = db.Column(db.String, nullable=False, default="")
    scenario = db.Column(
        db.String, nullable=False, default="inconclusive_scope_boundary"
    )
    posture = db.Column(db.String, nullable=False, default="not_started")
    summary = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.String, nullable=False, default=now_iso)
    updated_at = db.Column(db.String, nullable=False, default=now_iso)

    assessment = db.relationship("Assessment", back_populates="compliance_profiles")
    checks = db.relationship(
        "ComplianceCheck",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ComplianceCheck.sort_order",
    )


class ComplianceCheck(RecordMixin, db.Model):
    __tablename__ = "compliance_checks"

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(
        db.Integer,
        db.ForeignKey("compliance_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    fari_id = db.Column(db.String, nullable=False)
    control_id = db.Column(db.String, nullable=False)
    family = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    control_statement = db.Column(db.Text, default="")
    spd5_alignment = db.Column(db.String, nullable=False, default="supporting")
    principle_reference = db.Column(db.Text, default="")
    recommended_artifacts = db.Column(db.Text, default="")
    status = db.Column(db.String, nullable=False, default="not_verified")
    evidence_refs = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.String, nullable=False, default=now_iso)
    updated_at = db.Column(db.String, nullable=False, default=now_iso)

    profile = db.relationship("ComplianceProfile", back_populates="checks")


def init_app(app) -> None:
    db.init_app(app)
    with app.app_context():
        db.create_all()
        dialect = db.engine.dialect.name
        assessment_columns = {
            column["name"] for column in inspect(db.engine).get_columns("assessments")
        }
        if "revision_count" not in assessment_columns:
            db.session.execute(
                text(
                    "ALTER TABLE assessments ADD COLUMN "
                    "revision_count INTEGER NOT NULL DEFAULT 0"
                )
            )
            db.session.commit()
        columns = {column["name"] for column in inspect(db.engine).get_columns("findings")}
        if "include_sparta_countermeasures" not in columns:
            boolean_default = "0" if dialect == "sqlite" else "false"
            db.session.execute(
                text(
                    "ALTER TABLE findings ADD COLUMN "
                    f"include_sparta_countermeasures BOOLEAN NOT NULL DEFAULT {boolean_default}"
                )
            )
            db.session.commit()
        investigation_columns = {
            column["name"] for column in inspect(db.engine).get_columns("investigations")
        }
        if "scenario_state" not in investigation_columns:
            db.session.execute(
                text(
                    "ALTER TABLE investigations ADD COLUMN "
                    "scenario_state VARCHAR NOT NULL DEFAULT 'not_evaluated'"
                )
            )
            db.session.commit()


def next_sequence(records, prefix: str) -> int:
    """Return a stable next suffix even after records have been deleted."""
    maximum = 0
    for record in records:
        try:
            maximum = max(maximum, int(record.fari_id.rsplit("-", 1)[-1]))
        except (AttributeError, TypeError, ValueError):
            continue
    return maximum + 1
