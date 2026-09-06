# FARI language dictionaries

The web application loads `en.json` and `es.json` at startup. Templates use
stable keys such as `page.assessment_workspace`, while `human.*` keys translate
stored enum values without changing the values persisted in the database.

To review or extend the Spanish interface:

1. Add or edit the English source value in `en.json`.
2. Add the Spanish value with the same key in `es.json`.
3. Add a key to `english_exceptions.json` only when the English term is an
   intentional technical name or product term.
4. Open `/language/dictionary` in the web application to review missing,
   translated, and intentionally English entries.

User-entered assessment content, evidence, identifiers, and the canonical wiki
document are preserved as supplied. They are not machine-translated.
