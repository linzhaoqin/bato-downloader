"""Settings management for the application."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from utils.file_utils import get_default_download_root


@dataclass
class UserSettings:
    """Structure for user settings."""

    language: str = "en"
    download_dir: str = ""


class SettingsManager:
    """Manages loading and saving of user settings."""

    _instance: SettingsManager | None = None
    _settings_file = Path("settings.json")

    def __new__(cls) -> SettingsManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def __init__(self) -> None:
        # __init__ is called every time, but we only want to load once (handled in __new__)
        pass

    def _load(self) -> None:
        """Load settings from disk or initialize defaults."""
        self._data = UserSettings()
        
        if not self._settings_file.exists():
            # Set default download dir if not exists
            self._data = UserSettings(download_dir=get_default_download_root())
            self.save()
            return

        try:
            with open(self._settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Merge with defaults to handle missing keys in old files
                default_dict = asdict(UserSettings(download_dir=get_default_download_root()))
                default_dict.update(data)
                self._data = UserSettings(**default_dict)
        except (json.JSONDecodeError, OSError):
            # Fallback to defaults on error
            self._data = UserSettings(download_dir=get_default_download_root())

    def save(self) -> None:
        """Save current settings to disk."""
        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self._data), f, indent=2, ensure_ascii=False)
        except OSError:
            pass  # Log error in real app

    def get(self) -> UserSettings:
        """Get current settings."""
        return self._data

    def update(self, **kwargs: Any) -> None:
        """Update settings and save to disk."""
        current_dict = asdict(self._data)
        current_dict.update(kwargs)
        self._data = UserSettings(**current_dict)
        self.save()


# Global instance
SETTINGS = SettingsManager()
