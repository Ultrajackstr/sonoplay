# dlna/quirks.py
"""Device quirks registry for DLNA compatibility workarounds.

Sources:
- async_upnp_client: HEOS subscription timeout
- LMS-uPnP #63: Sony/Denon premature STOPPED
- go2tv #43: Sony HT-A9 workarounds
- Original repo #10: Timeout for WAN playback
"""

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from settings import settings

logger = logging.getLogger(__name__)

# Default quirk values
DEFAULT_QUIRKS: dict[str, Any] = {
    "ignore_premature_stopped": True,  # Most devices benefit from this
    "wait_for_can_play": False,        # Only enable for slow devices
    "subscription_timeout": None,       # None = use settings default
    "detect_end_by_elapsed": False,     # For devices that don't report track end
    "control_timeout": None,            # None = use settings default
}

# Known device quirks by manufacturer/model pattern
# Format: (manufacturer_pattern, model_pattern) -> quirk overrides
# Patterns are case-insensitive regexes
KNOWN_DEVICE_QUIRKS: dict[tuple[str, str], dict[str, Any]] = {
    # Sony devices: Emit STOPPED immediately after SetAVTransportURI
    # Source: LMS-uPnP #63, go2tv #43
    (r"sony", r".*"): {
        "ignore_premature_stopped": True,
        "wait_for_can_play": True,
    },
    # HEOS/Denon: 9-minute subscription timeout limit
    # Source: async_upnp_client CHANGES.rst
    (r"denon|heos", r".*"): {
        "subscription_timeout": 540,
        "ignore_premature_stopped": True,
    },
    # Marantz: Similar to Denon (same parent company)
    (r"marantz", r".*"): {
        "subscription_timeout": 540,
        "ignore_premature_stopped": True,
    },
    # Bose SoundTouch: Never reports track end
    # Source: LMS-uPnP userguide
    (r"bose", r"soundtouch"): {
        "detect_end_by_elapsed": True,
    },
}

# Cache for resolved quirks per device UUID
_quirks_cache: dict[str, dict[str, Any]] = {}


def _match_pattern(pattern: str, value: str | None) -> bool:
    """Check if value matches pattern (case-insensitive regex)."""
    if value is None:
        return False
    try:
        return bool(re.search(pattern, value, re.IGNORECASE))
    except re.error:
        return False


def _get_builtin_quirks(manufacturer: str | None, model: str | None) -> dict[str, Any]:
    """Get built-in quirks matching device manufacturer/model."""
    quirks: dict[str, Any] = {}
    for (mfr_pattern, model_pattern), device_quirks in KNOWN_DEVICE_QUIRKS.items():
        if _match_pattern(mfr_pattern, manufacturer) and _match_pattern(model_pattern, model):
            quirks.update(device_quirks)
    return quirks


def _get_user_quirks(uuid: str) -> dict[str, Any]:
    """Get user-configured quirks for device from settings."""
    from settings import settings
    data = settings.load_data()
    device_data = data.get(uuid, {})
    return device_data.get("quirks", {})


def _validate_quirks(quirks: dict[str, Any]) -> dict[str, Any]:
    """Validate and sanitize quirk values."""
    validated: dict[str, Any] = {}
    for key, value in quirks.items():
        if key not in DEFAULT_QUIRKS:
            logger.warning("Unknown quirk '%s' ignored", key)
            continue
        # Type validation
        if key == "subscription_timeout" and value is not None:
            try:
                value = min(max(int(value), 60), 3600)  # Clamp 60-3600
            except (TypeError, ValueError):
                continue
        if key == "control_timeout" and value is not None:
            try:
                value = min(max(float(value), 1.0), 60.0)  # Clamp 1-60
            except (TypeError, ValueError):
                continue
        if key in ("ignore_premature_stopped", "wait_for_can_play", "detect_end_by_elapsed"):
            value = bool(value)
        validated[key] = value
    return validated


def get_device_quirks(device: Any) -> dict[str, Any]:
    """Get merged quirks for a device (cached).
    
    Priority: user overrides > built-in patterns > defaults
    
    Args:
        device: DlnaDevice with uuid, manufacturer, model attributes
        
    Returns:
        Dict of quirk settings
    """
    uuid = getattr(device, "uuid", None)
    if uuid and uuid in _quirks_cache:
        return _quirks_cache[uuid]
    
    # Start with defaults
    quirks = DEFAULT_QUIRKS.copy()
    
    # Apply built-in patterns
    manufacturer = getattr(device, "manufacturer", None)
    model = getattr(device, "model", None)
    builtin = _get_builtin_quirks(manufacturer, model)
    quirks.update(_validate_quirks(builtin))
    
    # Apply user overrides
    if uuid:
        user = _get_user_quirks(uuid)
        quirks.update(_validate_quirks(user))
        _quirks_cache[uuid] = quirks
    
    return quirks


def clear_quirks_cache(uuid: str | None = None) -> None:
    """Clear cached quirks (call after user changes settings)."""
    if uuid:
        _quirks_cache.pop(uuid, None)
    else:
        _quirks_cache.clear()


def set_device_quirk(uuid: str, quirk: str, value: Any) -> None:
    """Set a user quirk override for a device."""
    from settings import settings
    if quirk not in DEFAULT_QUIRKS:
        raise ValueError(f"Unknown quirk: {quirk}")
    
    data = settings.load_data()
    device_data = data.get(uuid, {})
    quirks = device_data.get("quirks", {})
    quirks[quirk] = value
    device_data["quirks"] = quirks
    data[uuid] = device_data
    settings.save_data(data)
    clear_quirks_cache(uuid)
