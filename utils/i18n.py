"""Internationalization (i18n) utility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.settings import SETTINGS


class I18n:
    """Handles loading and retrieving translations."""

    _instance: I18n | None = None
    _locales_dir = Path("locales")
    _current_locale: str = "en"
    _translations: dict[str, Any] = {}

    def __new__(cls) -> I18n:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_initial_locale()
        return cls._instance

    def _load_initial_locale(self) -> None:
        """Load the locale defined in settings."""
        self.set_locale(SETTINGS.get().language)

    def set_locale(self, locale_code: str) -> None:
        """Switch the current locale and load the corresponding file."""
        self._current_locale = locale_code
        file_path = self._locales_dir / f"{locale_code}.json"
        
        if not file_path.exists():
            # Fallback to empty dict (will return keys) or try 'en'
            if locale_code != "en":
                self.set_locale("en")
                return
            self._translations = {}
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._translations = {}

    def get_locale(self) -> str:
        return self._current_locale

    def t(self, key: str, **kwargs: Any) -> str:
        """
        Get a translated string by key.
        Supports nested keys with dot notation (e.g., "menu.file.open").
        Supports format arguments (e.g., "Hello {name}", name="World").
        """
        keys = key.split(".")
        value: Any = self._translations
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
        
        if value is None or not isinstance(value, str):
            return key  # Return key if translation missing

        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return value


# Global instance
I18N = I18n()
