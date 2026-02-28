"""Sonoplay core configuration and settings.

This module provides the Settings class for application configuration,
and the atomic_write_json utility for safe JSON file writes.
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from datetime import datetime, timezone
import json
import logging
import os

logger = logging.getLogger(__name__)


def atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON data atomically using temp file + rename.
    
    This prevents data corruption if the process is killed or crashes
    during a write operation.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temp file in same directory (for atomic rename)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    
    try:
        with open(temp_path, mode="w") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is on disk
        
        # Atomic rename (works on POSIX, overwrites target if exists)
        os.replace(temp_path, path)
    except Exception:
        # Clean up temp file on failure
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:
                logger.debug("Expected cleanup error removing temp file: %s", e)
        raise


DEFAULT_STATS = {
    "play_count": 0,
    "play_duration_ms": 0,
    "status": "offline",
    "last_seen": None
}


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    http_port: int = 32488
    host_ip: str | None = None
    product: str = "SonoPlay"
    aliases: str = ""
    location_url: str | None = None
    version: str = "1"
    platform: str = "Linux"
    platform_version: str = "1"
    client_device: str | None = None
    client_device_name: str | None = None
    client_model: str | None = None
    client_profile: str | None = None
    plex_notify_interval: float = 0.5
    config_path: str = "config"
    data_file_name: str = "data.json"
    enable_onboarding_wizard: bool = True
    # Audio transcoding thresholds - exceeding these triggers Plex transcode
    # Sonos speakers typically support up to ~320kbps for network streams
    # and max 48kHz sample rate. CD quality is 1411 kbps at 44.1kHz.
    audio_transcode_threshold_kbps: int | None = 1500  # Safe default for most DLNA
    audio_transcode_max_sample_rate_hz: int | None = 48000  # Max for Sonos/most DLNA
    
    # HTTP timeout settings (in seconds)
    http_timeout_default: float = 10.0  # Default timeout for all requests
    http_timeout_connect: float = 5.0   # Connection timeout
    http_timeout_plex_tv: float = 10.0  # Timeout for plex.tv API requests
    http_timeout_dlna: float = 5.0      # Timeout for local DLNA device requests
    
    # Subscription and polling settings
    subscriber_ttl_seconds: int = 300   # How long before idle subscribers are cleaned up
    dlna_subscribe_timeout: int = 120   # DLNA event subscription timeout
    adapter_idle_interval: int = 60     # Seconds between state checks when idle
    pin_cache_max_size: int = 100       # Maximum cached Plex PIN login entries

    def __init__(self, **values):
        super().__init__(**values)
        object.__setattr__(self, "_data_cache", None)

    def dlna_name_alias(self, uuid: str, name: str, ip: str):
        data = self.load_data()
        alias = data.get(uuid, {}).get('alias', None)
        if alias is not None:
            return alias
        if not settings.aliases:
            return name
        aliases = settings.aliases.split(",")
        for alias in aliases:
            k, v = alias.split(":")
            if k.strip() in [uuid.strip(), name.strip(), ip.strip()]:
                return v.strip()
        return name

    def save_dlna_name_alias(self, uuid, alias):
        data = self.load_data()
        info = data.get(uuid, {})
        info['alias'] = alias
        data[uuid] = info
        self.save_data(data)

    def load_data(self):
        cache = getattr(self, "_data_cache", None)
        if cache is not None:
            return cache
        p = Path(self.config_path).joinpath(self.data_file_name)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            object.__setattr__(self, "_data_cache", {})
            return self._data_cache
        try:
            with open(p) as f:
                j = json.load(f)
                object.__setattr__(self, "_data_cache", j)
                return self._data_cache
        except Exception:
            object.__setattr__(self, "_data_cache", {})
            return self._data_cache

    def save_data(self, data):
        p = Path(self.config_path).joinpath(self.data_file_name)
        atomic_write_json(p, data)
        object.__setattr__(self, "_data_cache", data)

    def get_token_for_uuid(self, uuid):
        d = self.load_data()
        return d.get(uuid, {}).get("token", None)

    def set_token_for_uuid(self, uuid, token):
        d = self.load_data()
        info = d.get(uuid, {})
        info['token'] = token
        d[uuid] = info
        self.save_data(d)

    def get_device_stats(self, uuid):
        data = self.load_data()
        info = data.get(uuid, {})
        stats = info.get("stats", {})
        merged = DEFAULT_STATS.copy()
        merged.update(stats)
        return merged

    def _mutate_device_stats(self, uuid, mutator):
        data = self.load_data()
        info = data.get(uuid, {})
        stats = info.get("stats", {})
        merged = DEFAULT_STATS.copy()
        merged.update(stats)
        mutator(merged)
        info['stats'] = merged
        data[uuid] = info
        self.save_data(data)

    def update_device_stats(self, uuid, **kwargs):
        def mutator(stats):
            for key, value in kwargs.items():
                if isinstance(value, datetime):
                    value = value.isoformat()
                stats[key] = value
        self._mutate_device_stats(uuid, mutator)

    def increment_play_count(self, uuid):
        def mutator(stats):
            stats['play_count'] = stats.get('play_count', 0) + 1
            stats['status'] = 'playing'
            stats['last_seen'] = datetime.now(timezone.utc).isoformat()
        self._mutate_device_stats(uuid, mutator)

    def add_play_duration_ms(self, uuid, delta_ms):
        def mutator(stats):
            stats['play_duration_ms'] = stats.get('play_duration_ms', 0) + max(0, int(delta_ms))
            stats['last_seen'] = datetime.now(timezone.utc).isoformat()
        self._mutate_device_stats(uuid, mutator)

    def mark_device_status(self, uuid, status):
        self.update_device_stats(uuid, status=status, last_seen=datetime.now(timezone.utc))


# Global settings singleton
settings = Settings()
