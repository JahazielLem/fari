"""File-backed translations for the FARI web application."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from flask import g, has_request_context, session


SUPPORTED_LANGUAGES = ("en", "es")
DEFAULT_LANGUAGE = "en"


class TranslationCatalog:
    """Load editable JSON dictionaries and provide safe English fallbacks."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._catalogues = {
            language: self._load(language) for language in SUPPORTED_LANGUAGES
        }
        self._exceptions = self._load_exceptions()

    def _load(self, language: str) -> dict[str, str]:
        path = self.directory / f"{language}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        return payload if isinstance(payload, dict) else {}

    def _load_exceptions(self) -> dict[str, Any]:
        path = self.directory / "english_exceptions.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        return payload if isinstance(payload, dict) else {}

    @property
    def exceptions(self) -> dict[str, Any]:
        return self._exceptions

    def normalize(self, language: str | None) -> str:
        language = (language or DEFAULT_LANGUAGE).lower().replace("_", "-")
        language = language.split("-", 1)[0]
        return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    def language_options(self) -> list[tuple[str, str]]:
        return [
            ("en", self._catalogues["en"].get("language.english", "English")),
            ("es", self._catalogues["es"].get("language.spanish", "Español")),
        ]

    def get(self, key: str, language: str | None = None, **values: Any) -> str:
        language = self.normalize(language)
        english = self._catalogues["en"].get(key, key)
        value = self._catalogues[language].get(key, english)
        if values:
            try:
                return value.format(**values)
            except (KeyError, IndexError, ValueError):
                return value
        return value

    def human(self, value: Any, language: str | None = None) -> str:
        raw = "" if value is None else str(value)
        key = f"human.{raw.replace('-', '_')}"
        fallback = raw.replace("_", " ").replace("-", " ").title()
        language = self.normalize(language)
        english = self._catalogues["en"].get(key, fallback)
        return self._catalogues[language].get(key, english)

    def review(self, language: str | None = None) -> list[dict[str, Any]]:
        language = self.normalize(language)
        keys = sorted(set(self._catalogues["en"]) | set(self._catalogues[language]))
        exception_keys = set(self._exceptions.get("keys", []))
        return [
            {
                "key": key,
                "english": self._catalogues["en"].get(key, key),
                "selected": self._catalogues[language].get(
                    key, self._catalogues["en"].get(key, key)
                ),
                "translated": key in self._catalogues[language]
                and self._catalogues[language].get(key)
                != self._catalogues["en"].get(key),
                "english_exception": key in exception_keys,
            }
            for key in keys
        ]


def current_language() -> str:
    if has_request_context():
        catalog = getattr(g, "fari_catalog", None)
        if catalog is not None:
            return catalog.normalize(session.get("language"))
    return DEFAULT_LANGUAGE


@lru_cache(maxsize=4)
def load_catalog(directory: str) -> TranslationCatalog:
    return TranslationCatalog(Path(directory))


def translate(key: str, language: str | None = None, **values: Any) -> str:
    """Translate a key using the app catalog when available."""

    if has_request_context():
        catalog = getattr(g, "fari_catalog", None)
        if catalog is not None:
            return catalog.get(key, language or current_language(), **values)
    return key.format(**values) if values else key
