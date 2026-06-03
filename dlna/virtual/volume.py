"""Volume mapping utilities for heterogeneous device groups.

Maps between unified group volume (0-100) and device-specific volume ranges.
"""


def average_group_volume(volumes) -> int:
    """Average member volumes for a group, returning 0 for an empty list.

    Guards the group GetVolume against ZeroDivisionError when every member's
    volume read fails (so `volumes` is empty even though members exist).
    """
    if not volumes:
        return 0
    return sum(volumes) // len(volumes)


def group_volume(member_volumes):
    """Unified 0-100 volume for a group's web-UI slider: average the members
    that report a volume, or None when none do (so the UI hides the slider,
    matching a device with no volume). Reads cached member state rather than
    issuing a SOAP GetVolume per poll.
    """
    known = [v for v in member_volumes if v is not None]
    if not known:
        return None
    return average_group_volume(known)


def map_volume_to_device(
    group_volume: int,
    device_min: int,
    device_max: int,
) -> int:
    """Map 0-100 group volume to a device's actual volume range.
    
    Args:
        group_volume: Group volume as 0-100 percentage
        device_min: Device's minimum volume
        device_max: Device's maximum volume
        
    Returns:
        Scaled volume for the device, as an integer
    """
    # Clamp input to valid range
    group_volume = max(0, min(100, group_volume))
    
    # Handle edge case of same min/max
    if device_max == device_min:
        return device_min
    
    # Linear interpolation
    range_size = device_max - device_min
    scaled = device_min + (group_volume / 100) * range_size
    
    return int(round(scaled))

