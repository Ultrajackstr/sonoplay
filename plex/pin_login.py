from dlna.dlna_device import DlnaDevice
from utils import pms_header, xml2dict, g
from settings import settings
from datetime import datetime, timedelta, timezone
import aiohttp
import asyncio
import logging
import time

logger = logging.getLogger(__name__)

PINS = 'https://plex.tv/api/v2/pins'
CHECKPINS = 'https://plex.tv/api/v2/pins/{pin_id}'

# Cache PINs to avoid hammering plex.tv API
# Format: {uuid: {'pin': code, 'pin_id': id, 'expires': datetime, 'added': timestamp}}
_pin_cache = {}
PIN_CACHE_DURATION = timedelta(minutes=15)  # PINs are valid for 15 minutes


def cleanup_expired_pins() -> int:
    """Remove expired PINs from cache. Returns count of removed entries."""
    now = datetime.now(timezone.utc)
    expired_uuids = []
    
    for uuid, cached in _pin_cache.items():
        expires_str = cached.get('expires')
        if expires_str:
            # Handle both datetime objects and ISO strings
            if isinstance(expires_str, str):
                expires = datetime.fromisoformat(expires_str)
            else:
                expires = expires_str
            # Ensure timezone-aware comparison
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires <= now:
                expired_uuids.append(uuid)
    
    for uuid in expired_uuids:
        del _pin_cache[uuid]
    
    return len(expired_uuids)


def evict_if_needed() -> int:
    """Evict oldest entries if cache is at max size. Returns count of evicted entries."""
    max_size = settings.pin_cache_max_size
    if len(_pin_cache) < max_size:
        return 0
    
    # First, try to remove expired entries
    removed = cleanup_expired_pins()
    
    # If still at or over limit, evict oldest by 'added' timestamp
    if len(_pin_cache) >= max_size:
        # Sort by 'added' timestamp, oldest first
        sorted_entries = sorted(
            _pin_cache.items(),
            key=lambda x: x[1].get('added', 0)
        )
        # Remove oldest entry
        oldest_uuid = sorted_entries[0][0]
        del _pin_cache[oldest_uuid]
        removed += 1
    
    return removed


async def get_pin(device: DlnaDevice):
    """Get a PIN for the device, using cached value if available and not expired"""
    now = datetime.now(timezone.utc)
    
    # Evict if needed before adding new entry
    evict_if_needed()
    
    # Check if we have a cached PIN that hasn't expired
    if device.uuid in _pin_cache:
        cached = _pin_cache[device.uuid]
        if cached['expires'] > now:
            return cached['pin'], cached['pin_id']
    
    # Generate new PIN
    try:
        timeout = aiohttp.ClientTimeout(total=settings.http_timeout_plex_tv)
        async with g.http.post(PINS, headers=pms_header(device), timeout=timeout) as p:
            p.raise_for_status()
            d = xml2dict(await p.text())
            pin_code = d.pin['@code']
            pin_id = d.pin['@id']
            
            # Cache the PIN with added timestamp for LRU eviction
            _pin_cache[device.uuid] = {
                'pin': pin_code,
                'pin_id': pin_id,
                'expires': now + PIN_CACHE_DURATION,
                'added': time.time()
            }
            
            return pin_code, pin_id
    except asyncio.TimeoutError:
        logger.warning("Timeout getting PIN from plex.tv for %s", device.name)
        raise
    except Exception as e:
        logger.warning("Error getting PIN from plex.tv for %s: %s", device.name, e)
        raise


def clear_pin_cache(uuid: str):
    """Clear cached PIN for a device (called after successful linking)"""
    if uuid in _pin_cache:
        del _pin_cache[uuid]


async def check_pin(pin_id, device: DlnaDevice):
    try:
        timeout = aiohttp.ClientTimeout(total=settings.http_timeout_plex_tv)
        async with g.http.get(CHECKPINS.format(pin_id=pin_id), headers=pms_header(device), timeout=timeout) as p:
            if p.status == 404:
                return None
            p.raise_for_status()
            d = xml2dict(await p.text())
            return d.pin['@authToken']
    except asyncio.TimeoutError:
        logger.warning("Timeout checking PIN with plex.tv for %s", device.name)
        return None
    except Exception as e:
        logger.warning("Error checking PIN with plex.tv for %s: %s", device.name, e)
        return None
