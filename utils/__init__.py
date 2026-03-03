import aiohttp
import re
import xmltodict
from dotmap import DotMap

from settings import settings
from datetime import timedelta, datetime


UPNP_AVT_SERVICE_TYPE = "urn:schemas-upnp-org:service:AVTransport:1"
UPNP_RC_SERVICE_TYPE = "urn:schemas-upnp-org:service:RenderingControl:1"

# Device identifier validation patterns
# Accepts multiple formats used by DLNA/UPnP devices:
# 1. Standard UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# 2. Virtual devices: virtual-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# 3. Sonos RINCON: RINCON_XXXXXXXXXXXX (hex digits, typically 17 chars)
# 4. Generic alphanumeric device IDs (other vendors)
DEVICE_ID_PATTERN = re.compile(
    r'^(?:'
    r'(?:virtual-)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'  # Standard/virtual UUID
    r'|RINCON_[0-9A-F]{12,17}'  # Sonos RINCON format
    r'|uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'  # uuid: prefixed
    r'|[A-Za-z0-9_-]{8,64}'  # Generic alphanumeric (other DLNA devices)
    r')$',
    re.IGNORECASE
)

# Backward compatibility alias
UUID_PATTERN = DEVICE_ID_PATTERN


def is_valid_device_uuid(uuid: str | None) -> bool:
    """Validate a device identifier format.
    
    Accepts:
    - Standard UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    - Virtual device format: virtual-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    - Sonos RINCON format: RINCON_XXXXXXXXXXXX
    - Other DLNA device identifiers (alphanumeric, 8-64 chars)
    
    Args:
        uuid: The device identifier string to validate
        
    Returns:
        True if valid device identifier format, False otherwise
    """
    if uuid is None:
        return False
    return bool(DEVICE_ID_PATTERN.match(uuid))


def require_valid_uuid(uuid: str | None) -> None:
    """Validate UUID format and raise HTTPException if invalid.
    
    Use this at the start of endpoints that accept UUID parameters
    to ensure consistent 400 Bad Request responses for invalid UUIDs.
    
    Args:
        uuid: The UUID string to validate
        
    Raises:
        HTTPException: 400 status code if UUID format is invalid
    """
    from fastapi import HTTPException
    
    if not is_valid_device_uuid(uuid):
        raise HTTPException(
            status_code=400,
            detail="Invalid UUID format"
        )


class G(object):

    def __init__(self):
        self.http: aiohttp.ClientSession = None


g = G()


def unescape_xml(xml):
    from html import unescape
    return unescape(xml.decode())


def xml2dict(xml):
    if not isinstance(xml, str):
        xml = unescape_xml(xml)
    parsed = xmltodict.parse(xml,
                             process_namespaces=True,
                             namespaces={
                                 UPNP_AVT_SERVICE_TYPE: None,
                                 UPNP_RC_SERVICE_TYPE: None,
                                 "http://schemas.xmlsoap.org/soap/envelope/": None,
                                 "urn:schemas-upnp-org:event-1-0": None,
                                 "urn:schemas-upnp-org:metadata-1-0/AVT/": None
                             })
    return DotMap(parsed)


def pms_header(device):
    product = settings.product or device.model
    device_model = settings.client_model or device.model or product
    device_header = settings.client_device or device_model
    device_name = getattr(device, "name", None) or settings.client_device_name or product
    return {
        'X-Plex-Client-Identifier': device.uuid,
        'X-Plex-Device': device_header,
        'X-Plex-Device-Name': device_name,
        'X-Plex-Platform': settings.platform,
        'X-Plex-Platform-Version': settings.platform_version,
        'X-Plex-Product': product,
        'X-Plex-Version': settings.version,
        'X-Plex-Model': device_model,
        'X-Plex-Provides': 'player,pubsub-player',
        **({'X-Plex-Client-Profile-Name': settings.client_profile} if settings.client_profile else {})
    }


def plex_server_response_headers(device):
    product = settings.product or device.model
    device_model = settings.client_model or device.model or product
    device_header = settings.client_device or device_model
    device_name = getattr(device, "name", None) or settings.client_device_name or product
    return {
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Accept-Language': 'en',
        'X-Plex-Device': device_header,
        'X-Plex-Platform': settings.platform,
        'X-Plex-Platform-Version': settings.platform_version,
        'X-Plex-Product': product,
        'X-Plex-Version': settings.version,
        'X-Plex-Client-Identifier': device.uuid,
        'X-Plex-Device-Name': device_name,
        'X-Plex-Model': device_model,
        'X-Plex-Provides': 'player,pubsub-player',
        **({'X-Plex-Client-Profile-Name': settings.client_profile} if settings.client_profile else {})
    }


def subscriber_send_headers(device):
    product = settings.product or device.model
    device_model = settings.client_model or device.model or product
    device_header = settings.client_device or device_model
    device_name = getattr(device, "name", None) or settings.client_device_name or product
    return {
        'Content-Type': 'application/xml',
        'Connection': 'Keep-Alive',
        'X-Plex-Client-Identifier': device.uuid,
        'X-Plex-Platform': settings.platform,
        'X-Plex-Platform-Version': settings.platform_version,
        'X-Plex-Product': product,
        'X-Plex-Version': settings.version,
        'X-Plex-Device': device_header,
        'X-Plex-Device-Name': device_name,
        'X-Plex-Model': device_model,
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en,*',
        **({'X-Plex-Client-Profile-Name': settings.client_profile} if settings.client_profile else {})
    }


def timeline_poll_headers(device):
    return {
        'X-Plex-Client-Identifier': device.uuid,
        'X-Plex-Protocol': '1.0',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Max-Age': '1209600',
        'Access-Control-Expose-Headers': 'X-Plex-Client-Identifier',
        'Content-Type': 'text/xml;charset=utf-8'
    }


def extract_value(value, default=None):
    if value is None:
        return default
    if isinstance(value, DotMap):
        if '@val' in value:
            return extract_value(value['@val'], default)
        values = list(value.values())
        if len(values) == 1:
            return extract_value(values[0], default)
        return default if default is not None else value
    if isinstance(value, dict):
        if '@val' in value:
            return extract_value(value['@val'], default)
        values = list(value.values())
        if len(values) == 1:
            return extract_value(values[0], default)
        return default if default is not None else value
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return default
        return extract_value(value[0], default)
    return value


def _extract_time_value(value):
    extracted = extract_value(value, default="00:00:00")
    return str(extracted)


def parse_timedelta(value):
    s = _extract_time_value(value)
    if not s or s in ("NOT_IMPLEMENTED", "None"):
        return timedelta(0)
    try:
        t = datetime.strptime(s, "%H:%M:%S")
    except ValueError:
        if "." in s:
            base, _, _ = s.partition(".")
            try:
                t = datetime.strptime(base, "%H:%M:%S")
            except ValueError:
                return timedelta(0)
        else:
            return timedelta(0)
    delta = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    return delta


def convert_volume(value: int, from_max: int, from_min: int, to_max: int, to_min: int, to_step: int):
    if from_max == to_max and from_min == to_min:
        return value
    if from_max - from_min == to_max - to_min:
        return value - from_min + to_min
    from_range = from_max - from_min
    if from_range == 0:
        return to_min
    if to_step == 0:
        to_step = 1
    percent = float(value - from_min) / float(from_range)
    value = percent * (to_max - to_min)
    value = int(value / to_step)
    value += to_min
    return value
