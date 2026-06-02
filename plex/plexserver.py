# SPDX-License-Identifier: GPL-3.0-or-later
#
# Original work Copyright (C) 2021 songchenwen
# Modified work Copyright (C) 2025 plexdlnaplayer-enhanced contributors
#
# This file is part of plexdlnaplayer-enhanced, a fork of plexdlnaplayer.
# Original project: https://github.com/songchenwen/plexdlnaplayer
#
# Modifications from original:
#   - Added virtual device management REST API endpoints
#   - Added health check endpoint for container monitoring
#   - Complete web UI overhaul with modern templates
#   - Added device statistics and onboarding state endpoints
#   - Enhanced static file serving and template architecture
#   - Added API endpoints for device details and artwork
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from fastapi import FastAPI, Request, Header, Query, HTTPException, Form
from fastapi.responses import Response
from html import escape as xml_escape
from pydantic import BaseModel, Field
import uvicorn
import logging

from dlna import (
    get_device_by_uuid,
    get_device_data,
    DlnaDiscover,
    devices,
    list_virtual_devices,
    load_virtual_devices,
    list_virtual_devices_with_summaries,
    create_virtual_device,
    update_virtual_device,
    delete_virtual_device,
    list_physical_device_snapshots,
    VirtualDeviceError,
    CapabilityMismatchError,
    UnknownMemberError,
)
from typing import List, Optional, Dict, Any
from plex.subscribe import sub_man
from utils import plex_server_response_headers, xml2dict, timeline_poll_headers, g, require_valid_uuid, redact_token, spawn_task
from settings import settings
import asyncio
from dlna.dlna_device import DlnaDevice
from plex.adapters import adapter_by_device
from plex.gdm import PlexGDM
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from plex import pin_login
from datetime import datetime, timedelta, timezone
from version import VERSION
import aiohttp
import time


# Security note: This application assumes deployment on a trusted LAN.
# CORS is not enforced because:
# 1. The app runs on a home network behind NAT/firewall
# 2. DLNA devices require direct network access anyway
# 3. Plex authentication provides the main security boundary

# If exposing to untrusted networks, add CORS middleware.

XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'
XML_OK = XML_HEADER + '<Response code="200" status="OK"/>'

templates = Jinja2Templates(directory="templates")

# Server startup time for health endpoint
_startup_time: float = 0.0

# Logger for security-relevant events
logger = logging.getLogger(__name__)


class VirtualDeviceCreatePayload(BaseModel):
    name: str = Field(..., min_length=1)
    member_uuids: List[str] = Field(..., min_length=1)


class VirtualDeviceUpdatePayload(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    member_uuids: Optional[List[str]] = Field(default=None, min_length=1)


class OnboardingStateUpdate(BaseModel):
    completed: Optional[bool] = None
    steps: Optional[Dict[str, Any]] = Field(default=None)


class AudioSettingsUpdate(BaseModel):
    bitrate_kbps: Optional[int] = Field(default=None, ge=0, le=10000)
    sample_rate_hz: Optional[int] = Field(default=None, ge=0, le=384000)


plex_server = FastAPI()
s = plex_server
plex_server.mount("/static", StaticFiles(directory="static"), name="static")


# Global handler: when a DLNA device becomes unreachable mid-request,
# return 503 instead of letting the unhandled exception produce a 500.
from aiohttp import ClientConnectionError  # noqa: E402


@s.exception_handler(ClientConnectionError)
async def handle_device_unreachable(request: Request, exc: ClientConnectionError):
    logger.warning("device unreachable during request %s: %s", request.url.path, exc)
    return Response(
        content='<Response code="503" status="Device unreachable"/>',
        status_code=503,
        media_type="text/xml",
    )


def format_ms_to_hms(ms: int):
    total_seconds = max(0, int(ms // 1000))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


async def on_new_dlna_device(location_url):
    logger.info("got new dlna device location url %s", location_url)
    for d in devices:
        if d.location_url == location_url:
            return
    device = DlnaDevice(location_url)
    try:
        await device.get_data()
    except Exception as exc:
        logger.warning("failed to init dlna device from %s: %s", location_url, exc)
        return
    logger.info("got new dlna device from %s", device.name)
    spawn_task(device.loop_subscribe(), name=f"dlna sub {device.name}")
    devices.append(device)
    adapter = await adapter_by_device(device)
    settings.mark_device_status(device.uuid, "online")
    adapter.start_plex_tv_notify()
    gdm = PlexGDM(device)
    gdm.run()
    _gdm_instances.append(gdm)


_gdm_instances: list = []

dlna_discover = DlnaDiscover(on_new_dlna_device)


def _count_user_configured_devices() -> int:
    data = settings.load_data()
    count = 0
    for uuid, entry in data.items():
        if not isinstance(entry, dict):
            continue
        if str(uuid).startswith("__"):
            continue
        token = entry.get('token')
        alias = entry.get('alias')
        if token or alias:
            count += 1
    return count


async def guess_host_ip(request: Request):
    if settings.host_ip not in (None, "0.0.0.0"):
        return
    host = request.url.hostname or ""
    if host.startswith("127.") or host == "0.0.0.0":
        client_host = request.client.host if request.client else ""
        if client_host and not client_host.startswith("127.") and client_host != "0.0.0.0":
            host = client_host
        else:
            return
    settings.host_ip = host
    logger.info("guessed host ip %s", settings.host_ip)
    target_devices = list(devices)
    target_devices.extend(list_virtual_devices())
    for device in target_devices:
        adapter = await adapter_by_device(device)
        spawn_task(adapter.update_plex_tv_connection())


async def build_response(content: str, device: DlnaDevice = None, target_uuid: str = None, status_code: int = 200,
                         headers=None):
    if device is None and target_uuid is None:
        raise Exception("device and target uuid cannot both be none")
    if device is None:
        device = await get_device_by_uuid(target_uuid)
    if device is None:
        if headers is None:
            headers = {
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Accept-Language': 'en'}
            if target_uuid is not None:
                headers['X-Plex-Client-Identifier'] = target_uuid
    if headers is None:
        headers = plex_server_response_headers(device)
    return Response(content=content,
                    status_code=status_code,
                    headers=headers)


@s.on_event("startup")
async def on_startup():
    # Create HTTP session with default timeout
    timeout = aiohttp.ClientTimeout(
        total=settings.http_timeout_default,
        connect=settings.http_timeout_connect
    )
    g.http = aiohttp.ClientSession(timeout=timeout)
    # Restore the user's saved audio-transcode limits; without this they revert
    # to the class defaults on every restart.
    settings.load_persisted_audio_settings()
    await dlna_discover.discover()
    spawn_task(sub_man.start(), name="subscriber-manager")
    await sub_man.start_cleanup_task()
    await get_device_data()
    await load_virtual_devices()
    global _startup_time
    _startup_time = time.time()


@s.on_event("shutdown")
async def on_shutdown():
    await sub_man.stop_cleanup_task()
    sub_man.stop()
    # Stop all GDM instances to release UDP sockets
    for gdm in _gdm_instances:
        try:
            gdm.stop()
        except Exception:
            logger.debug("Error stopping GDM instance", exc_info=True)
    _gdm_instances.clear()
    stop_tasks = []
    for device in devices:
        adapter = await adapter_by_device(device)
        stop_tasks.append(adapter.stop())
        stop_tasks.append(device.remove_self())
    await asyncio.gather(*stop_tasks)
    if g.http:
        await g.http.close()


@s.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    virtual_devs = list_virtual_devices()
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - _startup_time) if _startup_time else 0,
        "devices": {
            "physical": len(devices),
            "virtual": len(virtual_devs)
        },
        "subscribers": sum(len(subs) for subs in sub_man.subscribers.values()),
        "version": VERSION
    }


@s.get("/api/plex-status")
async def plex_status():
    """Check if any device is connected to Plex."""
    # Check if any physical device has a Plex token
    for d in devices:
        adapter = await adapter_by_device(d)
        if adapter.plex_bind_token is not None:
            return {"connected": True}
    
    # Check if any virtual device has a Plex token
    virtual_devs = list_virtual_devices()
    for vd in virtual_devs:
        token = settings.get_token_for_uuid(vd.uuid)
        if token is not None:
            return {"connected": True}
    
    return {"connected": False}


@s.get("/")
async def link_page(request: Request):
    await guess_host_ip(request)
    ds = []
    for d in devices:
        adapter = await adapter_by_device(d)
        stats = adapter.stats_snapshot()
        play_duration = format_ms_to_hms(stats['play_duration_ms'])
        current_session = "--"
        if stats['current_session_ms'] > 0:
            current_session = format_ms_to_hms(stats['current_session_ms'])
        status = stats['status']
        if status == "playing":
            status_label = "Playing"
        elif status == "online":
            status_label = "Available"
        else:
            status_label = "Unavailable"
        status_class = {
            "playing": "lamp-playing",
            "online": "lamp-online",
            "offline": "lamp-offline"
        }.get(status, "lamp-offline")
        if adapter.plex_bind_token is not None:
            ds.append(dict(
                name=d.name,
                uuid=d.uuid,
                binded=True,
                status_label=status_label,
                status_class=status_class,
                ip=d.ip,
                play_count=stats['play_count'],
                play_duration=play_duration,
                current_session=current_session
            ))
        else:
            pin, pin_id = await pin_login.get_pin(d)
            ds.append(dict(
                name=d.name,
                uuid=d.uuid,
                pin=pin,
                pin_id=pin_id,
                binded=False,
                status_label=status_label,
                status_class=status_class,
                ip=d.ip,
                play_count=stats['play_count'],
                play_duration=play_duration,
                current_session=current_session
            ))
    return templates.TemplateResponse(
        "discovered_devices.html",
        {
            'devices': ds,
            'request': request,
            'onboarding_enabled': settings.enable_onboarding_wizard,
            'active_page': 'devices'
        }
    )


def _virtual_device_error_to_http(exc: Exception) -> None:
    if isinstance(exc, CapabilityMismatchError):
        raise HTTPException(
            status_code=400,
            detail={
                "type": "capability_mismatch",
                "message": str(exc),
                "offending_members": getattr(exc, "offending_members", []),
            },
        )
    if isinstance(exc, UnknownMemberError):
        raise HTTPException(
            status_code=404,
            detail={
                "type": "unknown_member",
                "message": str(exc),
                "member_uuid": exc.member_uuid,
            },
        )
    if isinstance(exc, VirtualDeviceError):
        raise HTTPException(status_code=400, detail={"message": str(exc)})
    raise exc


@s.get("/virtual-devices")
async def virtual_devices_page(request: Request):
    await guess_host_ip(request)
    return templates.TemplateResponse(
        "virtual_devices.html",
        {
            "request": request,
            "onboarding_enabled": settings.enable_onboarding_wizard,
            "active_page": "groups"
        }
    )


@s.get("/api/virtual-devices")
async def api_virtual_devices():
    virtual_devices = await list_virtual_devices_with_summaries()
    physical_devices = await list_physical_device_snapshots()
    return {
        "virtual_devices": virtual_devices,
        "physical_devices": physical_devices,
    }


@s.get("/api/onboarding")
async def api_get_onboarding_state():
    enabled = settings.enable_onboarding_wizard
    state = settings.datastore.get_onboarding_state()
    stored_devices = len(settings.datastore.get_all_device_uuids())
    user_configured_devices = _count_user_configured_devices()
    virtual_device_count = len(list_virtual_devices())
    eligible = bool(
        enabled
        and not state.get("completed")
        and user_configured_devices == 0
        and virtual_device_count == 0
    )
    return {
        "enabled": enabled,
        "completed": bool(state.get("completed", False)),
        "completed_at": state.get("completed_at"),
        "steps": state.get("steps", {}),
        "eligible": eligible,
        "stored_device_count": stored_devices,
        "user_configured_device_count": user_configured_devices,
        "virtual_device_count": virtual_device_count,
    }


@s.post("/api/onboarding")
async def api_update_onboarding_state(payload: OnboardingStateUpdate):
    if not settings.enable_onboarding_wizard:
        raise HTTPException(status_code=400, detail={"message": "Onboarding wizard disabled"})

    completed_at = None
    if payload.completed is True:
        completed_at = datetime.now(timezone.utc).isoformat()
    elif payload.completed is False:
        completed_at = None

    settings.datastore.set_onboarding_state(
        completed=payload.completed,
        steps=payload.steps if payload.steps is not None else None,
        completed_at=completed_at
    )

    state = settings.datastore.get_onboarding_state()
    stored_devices = len(settings.datastore.get_all_device_uuids())
    user_configured_devices = _count_user_configured_devices()
    virtual_device_count = len(list_virtual_devices())
    eligible = bool(
        settings.enable_onboarding_wizard
        and not state.get("completed")
        and user_configured_devices == 0
        and virtual_device_count == 0
    )

    return {
        "enabled": settings.enable_onboarding_wizard,
        "completed": bool(state.get("completed", False)),
        "completed_at": state.get("completed_at"),
        "steps": state.get("steps", {}),
        "eligible": eligible,
        "stored_device_count": stored_devices,
        "user_configured_device_count": user_configured_devices,
        "virtual_device_count": virtual_device_count,
    }


# ===================== Audio Settings API =====================

@s.get("/api/audio-settings")
async def api_get_audio_settings():
    """Get current audio transcoding settings."""
    stored = settings.datastore.get_audio_settings()
    return {
        "bitrate_kbps": stored.get("bitrate_kbps"),
        "sample_rate_hz": stored.get("sample_rate_hz"),
        # Include info about the slider ranges for the UI
        "presets": {
            "bitrate": [
                {"value": 0, "label": "Disabled", "description": "No bitrate limit"},
                {"value": 320, "label": "320 kbps", "description": "High-quality MP3"},
                {"value": 500, "label": "500 kbps", "description": "Safe for all DLNA"},
                {"value": 1000, "label": "1000 kbps", "description": "High-res lossy"},
                {"value": 1500, "label": "1500 kbps", "description": "CD quality safe (default)"},
                {"value": 3000, "label": "3000 kbps", "description": "Hi-Res audio"},
                {"value": 5000, "label": "5000 kbps", "description": "Studio quality"},
            ],
            "sample_rate": [
                {"value": 0, "label": "Disabled", "description": "No sample rate limit"},
                {"value": 44100, "label": "44.1 kHz", "description": "CD quality"},
                {"value": 48000, "label": "48 kHz", "description": "Sonos max (default)"},
                {"value": 96000, "label": "96 kHz", "description": "Hi-Res"},
                {"value": 192000, "label": "192 kHz", "description": "Studio quality"},
            ]
        }
    }


@s.post("/api/audio-settings")
async def api_update_audio_settings(payload: AudioSettingsUpdate):
    """Update audio transcoding settings."""
    settings.datastore.set_audio_settings(
        bitrate_kbps=payload.bitrate_kbps,
        sample_rate_hz=payload.sample_rate_hz
    )

    # Apply to the runtime settings so changes take effect immediately (same
    # path used at startup, keeping write and restore consistent).
    settings.load_persisted_audio_settings()
    stored = settings.datastore.get_audio_settings()
    logger.info("Audio settings updated: bitrate=%s kbps, sample_rate=%s Hz",
                stored.get("bitrate_kbps"), stored.get("sample_rate_hz"))
    
    return {
        "success": True,
        "bitrate_kbps": stored.get("bitrate_kbps"),
        "sample_rate_hz": stored.get("sample_rate_hz"),
    }


@s.post("/api/virtual-devices")
async def api_create_virtual_device(payload: VirtualDeviceCreatePayload):
    try:
        summary = await create_virtual_device(payload.name.strip(), payload.member_uuids)
        logger.info("Virtual device created: %s (%s)", summary.get('name', 'unknown'), summary.get('uuid', 'unknown'))
        return summary
    except Exception as exc:  # Translate known errors (always raises)
        _virtual_device_error_to_http(exc)


@s.put("/api/virtual-devices/{virtual_uuid}")
async def api_update_virtual_device(virtual_uuid: str, payload: VirtualDeviceUpdatePayload):
    require_valid_uuid(virtual_uuid)
    if payload.name is None and payload.member_uuids is None:
        raise HTTPException(status_code=400, detail={"message": "No changes supplied"})
    try:
        summary = await update_virtual_device(
            virtual_uuid,
            name=payload.name.strip() if payload.name else None,
            member_uuids=payload.member_uuids,
        )
        return summary
    except Exception as exc:  # Translate known errors (always raises)
        _virtual_device_error_to_http(exc)


@s.delete("/api/virtual-devices/{virtual_uuid}", status_code=204)
async def api_delete_virtual_device(virtual_uuid: str):
    require_valid_uuid(virtual_uuid)
    try:
        await delete_virtual_device(virtual_uuid)
        logger.info("Virtual device deleted: %s", virtual_uuid)
    except Exception as exc:
        _virtual_device_error_to_http(exc)
    return Response(status_code=204)


@s.get("/api/devices")
async def api_devices(request: Request):
    """API endpoint that returns device list with extended metadata including current track info."""
    await guess_host_ip(request)
    devices_list = []
    
    for d in devices:
        adapter = await adapter_by_device(d)
        stats = adapter.stats_snapshot()
        
        # Get current track info if available
        current_track = None
        artwork_urls = []
        plex_client = None
        
        # Get Plex client info if available
        if adapter.plex_lib and adapter.plex_lib.address:
            plex_client = {
                'protocol': adapter.plex_lib.protocol,
                'address': adapter.plex_lib.address,
                'port': adapter.plex_lib.port,
                'machine_id': adapter.plex_lib.machine_id
            }
        
        if adapter.current_track_info:
            track = adapter.current_track_info
            current_track = {
                'title': getattr(track, 'title', None),
                'artist': getattr(track, 'grandparentTitle', None),
                'album': getattr(track, 'parentTitle', None),
                'duration': getattr(track, 'duration', None),
                'position_ms': adapter.state.elapsed,
                'key': getattr(track, 'key', None),
                'ratingKey': getattr(track, 'ratingKey', None),
                'grandparentKey': getattr(track, 'grandparentKey', None),
                'parentKey': getattr(track, 'parentKey', None),
                'grandparentRatingKey': getattr(track, 'grandparentRatingKey', None),
                'parentRatingKey': getattr(track, 'parentRatingKey', None),
            }
            
            # Collect all available artwork URLs
            plex_lib = adapter.plex_lib
            if plex_lib and plex_lib.protocol and plex_lib.address:
                # Add Plex web URL for the track
                track_key = getattr(track, 'key', None)
                if track_key and plex_lib.machine_id:
                    current_track['plex_web_url'] = f"{plex_lib.protocol}://{plex_lib.address}:{plex_lib.port}/web/index.html#!/server/{plex_lib.machine_id}/details?key={track_key}"
                
                for attr in ['thumb', 'art', 'grandparentThumb', 'parentThumb']:
                    url = getattr(track, attr, None)
                    if url:
                        # Build full URL with Plex token
                        full_url = plex_lib.build_url(url, token=True)
                        artwork_urls.append(full_url)
        
        device_data = {
            'uuid': d.uuid,
            'name': d.name,
            'ip': d.ip,
            'model': d.model,
            'binded': adapter.plex_bind_token is not None,
            'status': stats['status'],
            'play_count': stats['play_count'],
            'play_duration_ms': stats['play_duration_ms'],
            'current_session_ms': stats['current_session_ms'],
            'current_track': current_track,
            'artwork_urls': artwork_urls,
            'plex_client': plex_client,
        }
        
        # Add PIN info for unbinded devices
        if not device_data['binded']:
            pin, pin_id = await pin_login.get_pin(d)
            device_data['pin'] = pin
            device_data['pin_id'] = pin_id
        
        devices_list.append(device_data)
    
    return {
        "devices": devices_list,
        "total_devices": len(devices_list)
    }


@s.post("/")
async def link_device(request: Request,
                      name: str = Form(default=None),
                      uuid: str = Form(...),
                      pin_id: str = Form(default=None),
                      relink: str = Form(default=None),
                      check_status: str = Form(default=None)):
    require_valid_uuid(uuid)
    device = await get_device_by_uuid(uuid)
    if device is None:
        raise HTTPException(404, f"device not found {uuid}")
    adapter = await adapter_by_device(device)
    
    # Handle status check request (for "Check Link" button)
    if check_status == 'true':
        # Always verify with plex.tv, not just check local token
        if adapter.plex_bind_token:
            # Verify the token is still valid with plex.tv
            try:
                async with g.http.get(
                    f"https://plex.tv/devices/{device.uuid}",
                    headers={"X-Plex-Token": adapter.plex_bind_token}
                ) as response:
                    if response.status == 200:
                        # Token is valid
                        return {"status": "linked", "message": "Device is currently linked"}
                    elif response.status in [401, 403, 404]:
                        # Token is invalid or device was unlinked - clear it
                        settings.set_token_for_uuid(uuid, None)
                        adapter.plex_bind_token = None
                        pin_login.clear_pin_cache(uuid)
                        # Fall through to generate new PIN below
                    else:
                        # Other error - assume still linked but warn
                        return {"status": "linked", "message": "Device appears linked (unable to verify with plex.tv)"}
            except Exception as e:
                # Network error or similar - assume still linked
                logger.warning("Error verifying device link with plex.tv: %s", e)
                return {"status": "linked", "message": "Device appears linked (unable to verify with plex.tv)"}
        
        # Device is not linked or token was invalid - generate PIN
        pin, new_pin_id = await pin_login.get_pin(device)
        return {"status": "not_linked", "pin": pin, "pin_id": new_pin_id, "message": "Device is not linked"}
    
    # Handle relink request
    if relink == 'true':
        # Remove the existing token to unlink the device
        settings.set_token_for_uuid(uuid, None)
        # Clear cached PIN and generate a new one
        pin_login.clear_pin_cache(uuid)
        pin, new_pin_id = await pin_login.get_pin(device)
        await adapter.update_plex_tv_connection()
        logger.info("Device unlinked from Plex: %s (%s)", device.name, uuid)
        return {"status": "unlinked", "pin": pin, "pin_id": new_pin_id}
    
    if pin_id:
        token = await pin_login.check_pin(pin_id, device)
        if token:
            settings.set_token_for_uuid(uuid, token)
            # Clear the cached PIN after successful linking
            pin_login.clear_pin_cache(uuid)
            await adapter.update_plex_tv_connection()
            logger.info("Device linked to Plex: %s (%s)", device.name, uuid)
            return {"status": "linked", "message": "Device successfully linked"}
        else:
            # Get the PIN to return it to the user
            pin, _ = await pin_login.get_pin(device)
            return {"status": "not_linked", "pin": pin, "pin_id": pin_id, "message": "Device not yet authenticated at plex.tv/link"}
    if name and name != device.name:
        device.name = name
        settings.save_dlna_name_alias(uuid, name)
        await adapter.update_plex_tv_connection()
    return await link_page(request)


@s.api_route("/dlna/callback/{uuid}", methods=["NOTIFY"])
async def dlna_subscribe(request: Request, uuid: str):
    require_valid_uuid(uuid)
    adapter = await adapter_by_device(await get_device_by_uuid(uuid))
    b = await request.body()
    info = xml2dict(b)
    if adapter is not None:
        adapter.update_state(info)
    return ""


@s.get("/player/playback/playMedia")
async def play_media(request: Request,
                     commandID: int,
                     containerKey: str,
                     key: str,
                     offset: int = 0,
                     paused: bool = False,
                     type_: str = Query("music", alias="type"),
                     target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
                     client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    await guess_host_ip(request)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    device = await get_device_by_uuid(target_uuid)
    if device is None:
        raise HTTPException(404)
    adapter = await adapter_by_device(device, request.query_params)
    if type_ == "music":
        await adapter.play_media(containerKey, key=key, offset=offset, paused=paused, query_params=request.query_params)
    else:
        await adapter.stop()
    return await build_response("", device=device)


@s.get("/player/playback/refreshPlayQueue")
async def refresh_play_queue(request: Request,
                             commandID: int,
                             playQueueID: int,
                             target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
                             client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    device = await get_device_by_uuid(target_uuid)
    if device is None:
        raise HTTPException(404)
    adapter = await adapter_by_device(device, request.query_params)
    await adapter.refresh_queue(playQueueID)
    return await build_response("", device=device)


async def _adapter_or_404(target_uuid: str):
    """Resolve the adapter for a music transport command, raising 404 if the
    device is unknown. Shared preamble for stop/next/prev/seek/skipTo/setParameters."""
    device = await get_device_by_uuid(target_uuid)
    if device is None:
        raise HTTPException(404, f"device not found {target_uuid}")
    return await adapter_by_device(device)


@s.get("/player/playback/play")
async def play(commandID: int,
               type_: str = Query("music", alias="type"),
               target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
               client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    device = await get_device_by_uuid(target_uuid)
    if device is None:
        raise HTTPException(404)
    adapter = await adapter_by_device(device)
    if type_ == "music":
        await adapter.play()
    else:
        await adapter.stop()
    return await build_response("", device=device)


@s.get("/player/playback/pause")
async def pause(commandID: int,
                type_: str = Query("music", alias="type"),
                target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
                client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    device = await get_device_by_uuid(target_uuid)
    if device is None:
        raise HTTPException(404)
    adapter = await adapter_by_device(device)
    if type_ == "music":
        await adapter.pause()
    return await build_response("", device=device)


@s.get("/player/playback/stop")
async def stop(request: Request,
               commandID: int,
               type_: str = Query("music", alias="type"),
               target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
               client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    await guess_host_ip(request)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    if type_ == "music":
        adapter = await _adapter_or_404(target_uuid)
        await adapter.stop()
    return await build_response(XML_OK, target_uuid=target_uuid)


@s.get("/player/playback/skipNext")
async def next_(commandID: int,
                type_: str = Query("music", alias="type"),
                target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
                client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    if type_ == "music":
        adapter = await _adapter_or_404(target_uuid)
        await adapter.next()
    return await build_response("", target_uuid=target_uuid)


@s.get("/player/playback/skipPrevious")
async def prev(commandID: int,
               type_: str = Query("music", alias="type"),
               target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
               client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    if type_ == "music":
        adapter = await _adapter_or_404(target_uuid)
        await adapter.prev()
    return await build_response("", target_uuid=target_uuid)


@s.get("/player/playback/seekTo")
async def seek(commandID: int,
               offset: int,
               type_: str = Query("music", alias="type"),
               target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
               client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    if type_ == "music":
        adapter = await _adapter_or_404(target_uuid)
        await adapter.seek(offset)
    return await build_response("", target_uuid=target_uuid)


@s.get("/player/playback/skipTo")
async def skip_to(commandID: int,
                  key: str,
                  type_: str = Query("music", alias="type"),
                  target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
                  client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    if type_ == "music":
        adapter = await _adapter_or_404(target_uuid)
        await adapter.skip_to_track(key)
    return await build_response("", target_uuid=target_uuid)


@s.get("/player/playback/setParameters")
async def set_parameters(commandID: int,
                         type_: str = Query("music", alias="type"),
                         shuffle: int = None,
                         repeat: int = None,
                         volume: float = None,
                         target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
                         client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    if type_ == 'music':
        adapter = await _adapter_or_404(target_uuid)
        if shuffle is not None:
            adapter.shuffle = shuffle
        if repeat is not None:
            adapter.queue.repeat = repeat
        if volume is not None:
            await adapter.set_volume(int(volume))
    return await build_response("", target_uuid=target_uuid)


_poll_lock = asyncio.Lock()
_waiting_poll_count = 0

@s.get("/player/timeline/poll")
async def timeline_poll(request: Request,
                        commandID: int,
                        wait: int = 0,
                        target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
                        client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    global _waiting_poll_count
    async with _poll_lock:
        _waiting_poll_count += 1
        current_count = _waiting_poll_count
    try:
        if current_count > 3:
            logger.debug("High poll count: %s", current_count)
        begin_time = datetime.now(timezone.utc)
        await guess_host_ip(request)
        sub_man.update_command_id(target_uuid, client_uuid, commandID)
        device = await get_device_by_uuid(target_uuid)
        if device is None:
            raise HTTPException(404, f"device not found {target_uuid}")
        if hasattr(device, "loop_subscribe"):
            spawn_task(device.loop_subscribe())
        adapter = await adapter_by_device(device)
        if wait == 1:
            await adapter.wait_for_event(settings.plex_notify_interval * 20, interesting_fields=[
                'state', 'volume', 'current_uri', 'elapsed_jump'])
        msg = await sub_man.msg_for_device(device)
        while msg is None:
            logger.debug("Waiting for message: %s", target_uuid)
            await asyncio.sleep(settings.plex_notify_interval)
            msg = await sub_man.msg_for_device(device)
        msg = msg.format(command_id=commandID)
        if datetime.now(timezone.utc) - begin_time >= timedelta(milliseconds=500):
            logger.debug("Slow poll request: %s took %s", redact_token(str(request.url)), datetime.now(timezone.utc) - begin_time)
        spawn_task(sub_man.notify_server_device(device, force=True))
        return await build_response(msg, device=device, headers=timeline_poll_headers(device))
    finally:
        async with _poll_lock:
            _waiting_poll_count -= 1


@s.get("/player/timeline/subscribe")
async def subscribe(request: Request,
                    commandID: int,
                    port: int,
                    protocol: str = "http",
                    target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
                    client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    await guess_host_ip(request)
    device = await get_device_by_uuid(target_uuid)
    if device is None:
        raise HTTPException(404, f"device not found {target_uuid}")
    await sub_man.add_subscriber(target_uuid, client_uuid, request.client.host, port, protocol=protocol, command_id=commandID)
    return await build_response(XML_OK, target_uuid=target_uuid)


@s.get("/player/timeline/unsubscribe")
async def unsubscribe(request: Request,
                      commandID: int,
                      target_uuid: str = Header(None, alias="x-plex-target-client-identifier"),
                      client_uuid: str = Header(None, alias="x-plex-client-identifier")):
    require_valid_uuid(target_uuid)
    await guess_host_ip(request)
    sub_man.update_command_id(target_uuid, client_uuid, commandID)
    await sub_man.remove_subscriber(client_uuid, target_uuid=target_uuid)
    return await build_response(XML_OK, target_uuid=target_uuid)


@s.get("/resources")
async def resources(request: Request, target_uuid: str = Header(None, alias="x-plex-target-client-identifier")):
    require_valid_uuid(target_uuid)
    await guess_host_ip(request)
    device = await get_device_by_uuid(target_uuid)
    if device is None:
        raise HTTPException(404, f"no device {target_uuid}")
    logger.debug("resource for %s", device.name)
    res = "<MediaContainer>"
    res += f'<Player title="{xml_escape(str(device.name), quote=True)}" protocol="plex" protocolVersion="1" ' \
           f'protocolCapabilities="timeline,playback,playqueues" ' \
           f'machineIdentifier="{device.uuid}" product="{device.model}" ' \
           f'platform="{settings.platform}" ' \
           f'platformVersion="{settings.platform_version}" ' \
           f'version="{settings.version}" deviceClass="stb"/>'
    res += "</MediaContainer>"
    return await build_response(res, device=device)


@s.get("/player/mirror/details")
async def mirror(target_uuid: str = Header(None, alias="x-plex-target-client-identifier")):
    require_valid_uuid(target_uuid)
    device = await get_device_by_uuid(target_uuid)
    if device is None:
        raise HTTPException(404, f'device not found {target_uuid}')
    return await build_response("", target_uuid=target_uuid)


class SuppressNoisyHTTPLogsFilter(logging.Filter):
    """Filter out noisy HTTP access logs for specific endpoints"""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "/api/devices" in msg:
            return False
        if "/player/timeline/poll" in msg:
            return False
        return True


def start_plex_server(port=None):
    if port is None:
        port = settings.http_port
    
    # Configure logging to suppress noisy HTTP endpoints
    logging.getLogger("uvicorn.access").addFilter(SuppressNoisyHTTPLogsFilter())
    
    return uvicorn.run("plex:plex_server", host="0.0.0.0", port=port)


if __name__ == "__main__":
    start_plex_server(settings.http_port)
