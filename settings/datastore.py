# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 plexdlnaplayer-enhanced contributors
#
# This file is part of plexdlnaplayer-enhanced, a fork of plexdlnaplayer.
# Original project: https://github.com/songchenwen/plexdlnaplayer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
DataStore abstraction layer for future database migration.
Currently backed by JSON files, but can be swapped for SQLAlchemy/ORM later.

Only meta-scoped settings (onboarding, audio, device-uuid listing) live here;
per-device stats/token/alias persistence is handled directly on the Settings
object (the previous duplicate DataStore methods were never wired in).
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Callable
from copy import deepcopy


class DataStore(ABC):
    """Abstract interface for data persistence operations."""

    @abstractmethod
    def get_all_device_uuids(self) -> list[str]:
        """Get list of all known device UUIDs."""
        pass

    @abstractmethod
    def get_onboarding_state(self) -> Dict[str, Any]:
        """Return onboarding wizard state and flags."""
        pass

    @abstractmethod
    def set_onboarding_state(self, *, completed: Optional[bool] = None,
                              steps: Optional[Dict[str, Any]] = None,
                              completed_at: Optional[str] = None) -> None:
        """Persist onboarding wizard state changes."""
        pass

    @abstractmethod
    def get_audio_settings(self) -> Dict[str, Any]:
        """Get audio transcoding settings."""
        pass

    @abstractmethod
    def set_audio_settings(self, *, bitrate_kbps: Optional[int] = None,
                            sample_rate_hz: Optional[int] = None) -> None:
        """Persist audio transcoding settings."""
        pass


# Default audio settings. None = "no limit" (direct play, no transcode), which
# matches the runtime Settings defaults (audio_transcode_* = None). Keeping these
# in sync matters: the datastore is loaded into the runtime settings at startup,
# so a non-None default here would silently force transcoding on a fresh install
# and make the UI (which reads these) disagree with the engine. Set a limit only
# for devices that need it (some Sonos models), via the web UI.
DEFAULT_AUDIO_SETTINGS = {
    "bitrate_kbps": None,
    "sample_rate_hz": None,
}

DEFAULT_ONBOARDING_STATE = {
    "completed": False,
    "completed_at": None,
    "steps": {}
}


class JSONDataStore(DataStore):
    """JSON file-based implementation of DataStore."""

    def __init__(self, settings_instance):
        """Initialize with reference to existing Settings instance."""
        self._settings = settings_instance

    _META_KEY = "__meta__"

    def _load_data(self) -> Dict[str, Any]:
        return dict(self._settings.load_data())

    def _mutate_meta(self, mutator: Callable[[Dict[str, Any]], None]) -> None:
        data = self._load_data()
        meta = dict(data.get(self._META_KEY, {}))
        mutator(meta)
        data[self._META_KEY] = meta
        self._settings.save_data(data)

    def get_all_device_uuids(self) -> list[str]:
        """Get list of all known device UUIDs."""
        data = self._load_data()
        return [uuid for uuid in data.keys() if uuid != self._META_KEY]

    def get_onboarding_state(self) -> Dict[str, Any]:
        data = self._load_data()
        meta = dict(data.get(self._META_KEY, {}))
        onboarding = deepcopy(DEFAULT_ONBOARDING_STATE)
        stored_state = meta.get("onboarding", {})
        if isinstance(stored_state, dict):
            onboarding.update({k: v for k, v in stored_state.items() if k in onboarding})
            steps = stored_state.get("steps", {})
            onboarding["steps"] = steps if isinstance(steps, dict) else {}
        else:
            onboarding["steps"] = {}
        return onboarding

    def set_onboarding_state(self, *, completed: Optional[bool] = None,
                              steps: Optional[Dict[str, Any]] = None,
                              completed_at: Optional[str] = None) -> None:
        def mutator(meta: Dict[str, Any]) -> None:
            onboarding = dict(meta.get("onboarding", {}))
            if completed is not None:
                onboarding["completed"] = bool(completed)
            if steps is not None:
                onboarding["steps"] = dict(steps)
            if completed_at is not None:
                onboarding["completed_at"] = completed_at
            meta["onboarding"] = onboarding

        self._mutate_meta(mutator)

    def get_audio_settings(self) -> Dict[str, Any]:
        """Get audio transcoding settings from storage or defaults."""
        data = self._load_data()
        meta = dict(data.get(self._META_KEY, {}))
        audio = deepcopy(DEFAULT_AUDIO_SETTINGS)
        stored = meta.get("audio_settings", {})
        if isinstance(stored, dict):
            # Only update keys that exist in defaults
            audio.update({k: v for k, v in stored.items() if k in audio})
        return audio

    def set_audio_settings(self, *, bitrate_kbps: Optional[int] = None,
                            sample_rate_hz: Optional[int] = None) -> None:
        """Persist audio transcoding settings."""
        def mutator(meta: Dict[str, Any]) -> None:
            audio = dict(meta.get("audio_settings", {}))
            if bitrate_kbps is not None:
                audio["bitrate_kbps"] = int(bitrate_kbps) if bitrate_kbps > 0 else None
            if sample_rate_hz is not None:
                audio["sample_rate_hz"] = int(sample_rate_hz) if sample_rate_hz > 0 else None
            meta["audio_settings"] = audio

        self._mutate_meta(mutator)
