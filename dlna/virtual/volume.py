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


def map_device_to_group_volume(
    device_volume: int,
    device_min: int,
    device_max: int,
) -> int:
    """Map a device's volume to 0-100 group percentage.
    
    Args:
        device_volume: Current device volume
        device_min: Device's minimum volume
        device_max: Device's maximum volume
        
    Returns:
        Group volume as 0-100 percentage
    """
    # Handle edge case of same min/max
    if device_max == device_min:
        return 100 if device_volume >= device_min else 0
    
    # Inverse linear interpolation
    range_size = device_max - device_min
    percentage = ((device_volume - device_min) / range_size) * 100
    
    return int(round(max(0, min(100, percentage))))
