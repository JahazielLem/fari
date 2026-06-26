# FARI Repository Architecture

FARI is organized as a single repository with two deliberately separate layers:

- `spec/`: the framework contract, documentation, schema, examples, templates, and releases.
- `webapp/`: the Flask implementation that helps users execute the FARI workflow.

The web application is not the framework. It is one implementation of the
framework. This keeps FARI publishable as a methodology while still allowing the
web app to move quickly.

## Specification Layer

`spec/current/` is the editable source of truth:

- `spec/current/specification/` contains the current Markdown specification.
- `spec/current/templates/` contains manual report templates.
- `spec/current/reports/` contains scenario catalogs and example reports.
- `spec/current/fari.manifest.yml` describes the version and web contract.

`spec/schema/` contains machine-readable contracts consumed by tooling and
downloaded from the web app.

`spec/releases/` contains immutable versioned outputs. Release generation should
copy from `spec/current/` into `spec/releases/vX.Y.Z/_sources/` and render PDFs
from that snapshot.

## Web Layer

`webapp/` contains the operational edition:

- guided assessment workflow
- evidence upload
- SPARTA and Attack Flow visualization
- SBOM inventory
- SPD-5 companion checklist
- report generation
- PostgreSQL or SQLite persistence

The web layer reads framework materials from `spec/`. If a field, conclusion
state, segment, access basis, or report section changes in the framework, update
`spec/current/fari.manifest.yml`, the schema, the web UI, and tests together.

## Dependency Direction

Allowed:

- `webapp/` reads from `spec/`
- `tools/` reads and writes `spec/current` and `spec/releases`
- `tests/` validate both the web workflow and the framework contract

Avoid:

- putting normative framework text inside `webapp/templates`
- making the web app the only place where a field is defined
- modifying `spec/releases` by hand after a release is generated

## Release Rule

Every release should include:

- PDF specification
- PDF manual template
- scenario catalog
- source snapshot
- schema version
- framework version in generated reports
