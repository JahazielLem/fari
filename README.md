# FARI

**Framework for Aerospace Research and Investigation**

FARI is a documentation and assurance framework for organizing heterogeneous
security assessments of space systems. It does not replace the auditor's
preferred technical methodology. It defines the common context, evidence,
traceability, qualitative conclusion, and executive outputs that every
assessment must produce.

FARI is designed to answer:

> Given assessments performed by different teams, tools, and methods, what can
> the mission owner confidently conclude about mission risk, evidence coverage,
> and required action?

Its reporting workflow explicitly separates an external **Evidence Producer**
from the **Report Author**. The evidence producer may supply arbitrary material
without knowing FARI or completing a FARI form. The Report Author performs all
FARI normalization, contextual completion, mapping, conclusion, and reporting.

## Core Documents

- [FARI Specification PDF](spec/releases/v1.3.0/specification/FARI-Specification-v1.3.0.pdf) -
  finalized versioned specification bundle.
- [FARI Manual Template PDF](spec/releases/v1.3.0/manual-template/FARI-Manual-Template-v1.3.0.pdf) -
  finalized manual fill template.
- [Scenario Test Catalog PDF](spec/releases/v1.3.0/reports/FARI-SCENARIO-TEST_CATALOG-v1.3.0.pdf) -
  seeded validation portfolio for the framework.

## Examples

1. [Minimal Source Review](examples/01-minimal-source-review.md)
2. [Firmware Assessment with QEMU](examples/02-qemu-firmware-assessment.md)
3. [Mission-Wide Multi-Team Assessment](examples/03-mission-wide-assessment.md)
4. [Operational LEO Reset Command Replay](examples/04-operational-leo-reset-replay.md)

## Case Reports

- [Versioned release reports](spec/releases/v1.3.0/reports)

## Quick Reference

- Current editable framework sources live in `spec/current/`.
- Versioned release artifacts live in `spec/releases/v1.3.0/`.
- The web application reads the same specification sources through the internal
  wiki, help modal, resource downloads, and report generation.

## Repository Layout

```text
spec/                  Canonical framework layer
  current/             Editable Markdown specification, templates, scenario catalog, manifest
  schema/              Machine-readable FARI assessment contract
  releases/            Immutable versioned PDFs and source snapshots
webapp/                Flask implementation of the guided workflow
tools/                 Builders, release generators, and scenario seed scripts
tests/                 Web and persistence tests
cases/                 Supplied evidence and raw test material
```

The contract between framework and implementation is explicit in
`spec/current/fari.manifest.yml`. Framework changes should start in `spec/current`
and then be reflected in the web app, schema, and tests together. Run
`python tools/check_spec_parity.py` to verify controlled values, source formats,
specification copies, and removed integrations remain aligned.

## Web Application

The Python web application implements the guided FARI Report Author workflow,
evidence upload, configurable SQL persistence, integrated
wiki, assessment traceability with captured revisions, and per-asset technical source inventory
timelines, versioned report generation, resource downloads, consolidated report
generation, and bilingual EN/ES interface and report output.

- Run with `docker compose up --build`, then open `http://localhost:8081`.
- Default local login is `fari` / `toor`. Change it with
  `FARI_LOGIN_USERNAME` and `FARI_LOGIN_PASSWORD`.
- The workspace uses a collapsible sidebar, a resources section for manual
  templates, and an integrated help modal opened with `Ctrl/Cmd + K`.
- Use the `EN` / `ES` selector in the header to change the session language.
  Generated DOCX/PDF reports use the selected language for their labels.
- The editable dictionaries are in `webapp/translations/en.json` and
  `webapp/translations/es.json`. Review technical terms kept in English with
  `webapp/translations/english_exceptions.json` and the protected review page
  at `/language/dictionary`.
- Set `FARI_DEFAULT_LANGUAGE=es` to start new sessions in Spanish. User-entered
  content, evidence, identifiers, and canonical wiki text remain unchanged.
- Docker Compose starts PostgreSQL by default and creates named volumes for
  uploaded evidence (`fari_data`) and database records (`fari_postgres_data`).

### Static / GitHub Pages Direction

The current Flask app is the operational edition: it supports login, uploads,
report generation, PostgreSQL/SQLite persistence, and server-side DOCX/PDF
generation.

A GitHub Pages edition should be a separate static implementation that consumes
`spec/current/fari.manifest.yml`, `spec/schema/fari-assessment.schema.json`, and
the Markdown/PDF resources, but does not send evidence or reports to a server.
Recommended storage modes:

- Browser-only draft storage with IndexedDB for structured assessments and
  evidence metadata.
- File System Access API for optional local project folders in Chromium-based
  browsers.
- Import/export as encrypted or plain JSON bundles so users control when data
  leaves the browser.
- Client-side PDF/Markdown generation for simple reports, with server-side
  DOCX/PDF reserved for the Flask edition.

Avoid treating browser local storage as secure storage for sensitive evidence.
For public GitHub Pages, the safest default is: keep examples public, keep real
client material local to the user's browser, and provide explicit export/delete
controls.

### Database Access

The backend reads `FARI_DATABASE_URL` first, then `DATABASE_URL`, and falls back
to local SQLite at `/data/fari.sqlite3` when no external URL is provided.

With the default Docker Compose configuration, PostgreSQL is exposed on the host:

```bash
docker compose up --build
psql postgresql://fari:toor@localhost:5432/fari
```

If port `5432` is already in use, publish PostgreSQL on another local port:

```bash
FARI_POSTGRES_PORT=15432 docker compose up --build
psql postgresql://fari:toor@localhost:15432/fari
```

To keep using SQLite inside the Docker data volume:

```bash
FARI_DATABASE_URL=sqlite:////data/fari.sqlite3 docker compose up --build
```

## Positioning

```mermaid
flowchart TB
    FARI["FARI<br/>Frame, Acquire, Relate, Inform<br/>conclusion, assurance, executive reporting"]

    ATTACK["MITRE ATT&CK<br/>Enterprise and ground-system TTPs"]
    NIST["NIST / ISO / ECSS / organization controls<br/>Governance and compliance"]

    METHODS["Auditor-selected methods<br/>Firmware | RF | Hardware | Cloud | Web | Supply chain"]

    METHODS --> FARI
    ATTACK --> FARI
    NIST --> FARI
```

FARI is intentionally framework-neutral. External mappings may be recorded when
an engagement requires them, but they never replace the evidence, claim, scope,
or conclusion model.

## Status

This repository contains the current canonical FARI specification and the
working Python web application built from that same workflow.

Case evidence is stored in `cases/`. Versioned FARI-authored documentation is
stored in `spec/releases/`, preserving a clear boundary between supplied evidence
and generated analysis. Every investigation ends with a qualitative FARI Conclusion:
`Meets`, `Does Not Meet`, `Inconclusive`, or `Not Assessed`. Assessments with
multiple investigations also produce one consolidated report.

## Recommended Adoption Path

1. Pilot the records and templates on one firmware assessment.
2. Pilot a cross-segment assessment with at least two independent technical
   teams.
3. Refine conclusion governance and gating-claim definitions using pilot evidence.
4. Stabilize a versioned exchange format and conformance tests.
5. Build the web application around the stabilized records and workflows.

The first implementation priority should be traceability, conclusive reporting,
and easy Report Author workflows, not automated scoring.
