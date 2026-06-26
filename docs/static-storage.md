# Static FARI Edition and Local Storage Options

The Flask app is the operational edition of FARI. It uses PostgreSQL or SQLite
because it manages uploaded evidence, report generation, user sessions, and
server-side files.

A GitHub Pages edition should be a separate static web app. It can consume the
same `spec/` assets, but it should not require a database or server.

## Recommended Static Architecture

```text
static-app/
  index.html
  assets/
  fari-static.js
  fari-storage.js
  fari-report.js
spec/
  current/
  schema/
  releases/
```

The static app should load:

- `spec/current/fari.manifest.yml`
- `spec/schema/fari-assessment.schema.json`
- public examples and templates

It should never upload real assessment data by default.

## Storage Options

### IndexedDB

Best default for browser-only drafts.

Use it for:

- assessments
- assets
- investigations
- findings
- SPD-5 checklist state
- SBOM component metadata
- local evidence metadata

Pros:

- works on GitHub Pages
- better than `localStorage` for structured data
- supports larger records
- asynchronous and suitable for offline use

Limits:

- browser-local only
- can be cleared by the user or browser policy
- not secure storage by itself

### localStorage

Use only for small preferences:

- theme
- sidebar state
- last opened assessment id

Avoid using it for assessment content or evidence because it is synchronous,
small, and easy to inspect.

### File System Access API

Useful optional mode for Chromium-based browsers.

Use it to let users select a local project folder and save:

- `assessment.json`
- generated Markdown
- exported evidence index
- local report drafts

Pros:

- strong user control
- no server
- project-folder workflow feels natural

Limits:

- not supported equally by all browsers
- requires explicit user permission

### JSON Import / Export

This should exist in every static edition.

Use:

- `Export assessment bundle`
- `Import assessment bundle`
- `Delete local workspace`

The exported bundle can match `spec/schema/fari-assessment.schema.json`.

### Encrypted Export Bundle

Optional but useful for sensitive workflows.

The browser can encrypt exported JSON using a passphrase with Web Crypto before
the file is downloaded. This protects the file at rest, but it does not make
browser storage itself secure.

## Security Posture

For GitHub Pages:

- store only public examples in the repository
- keep real client data in the user's browser or downloaded files
- provide explicit delete/export controls
- avoid telemetry
- avoid remote APIs by default
- warn users that browser storage is not a secure evidence vault

## Practical MVP Split

Keep two editions:

- **FARI Operational**: Flask + PostgreSQL/SQLite + Docker, for real internal use.
- **FARI Static**: GitHub Pages + IndexedDB + JSON import/export, for demos,
  public education, and low-sensitivity local drafting.

Both editions should consume the same `spec/` folder and schema.
