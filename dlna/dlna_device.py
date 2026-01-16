# SPDX-License-Identifier: GPL-3.0-or-later
#
# Original work Copyright (C) 2021 songchenwen
# Modified work Copyright (C) 2025 plexdlnaplayer-enhanced contributors
#
# This file is part of plexdlnaplayer-enhanced, a fork of plexdlnaplayer.
# Original project: https://github.com/songchenwen/plexdlnaplayer
#
# Modifications from original:
#   - Added graceful error handling for missing DLNA attributes
#   - Enhanced HTTP timeout handling for unresponsive devices
#   - Added device status tracking and statistics
#   - Improved XML escaping for metadata
#   - Added local IP detection for multi-homed hosts
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import asyncio
import logging
import re
import traceback
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)
from datetime import datetime, timedelta, timezone
from html import escape as xml_escape

import aiohttp
from aiohttp import ClientConnectorError, ClientConnectionError

from plex.adapters import remove_adapter
from utils import xml2dict, UPNP_RC_SERVICE_TYPE, UPNP_AVT_SERVICE_TYPE, g, extract_value
from dlna.discover import guess_local_ip
from settings import settings

PAYLOAD_FMT = '<?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" ' \
              's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:{action} xmlns:u="{urn}">' \
              '{fields}</u:{action}></s:Body></s:Envelope>'


DEFAULT_ACTION_DATA = {
    "InstanceID": 0,
    "Channel": "Master",
    "CurrentURIMetaData": "",
    "NextURIMetaData": "",
    "Unit": "REL_TIME",
    "Speed": 1
}

ERROR_COUNT_TO_REMOVE = 20
MAX_RETRIES = 3


class ServerErrorException(Exception):
    """Raised for HTTP 5xx errors that should be retried."""
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {(body or '')[:100]}")


def sanitize_soap_response(xml: str) -> str:
    """Fix known SOAP/XML quirks from non-compliant devices.
    
    Known issues:
    - Oppo: Returns <& instead of <s: for envelope namespace prefix
      (both in tags like <&Envelope and in namespace declarations xmlns:&=)
    
    Future quirks should be added here as discovered.
    """
    # Fix Oppo malformed namespace prefix (order matters - do xmlns first)
    xml = xml.replace('xmlns:&=', 'xmlns:s=')
    xml = xml.replace('<&', '<s:')
    xml = xml.replace('</&', '</s:')
    return xml


# Device list and lock for thread-safe access
devices = []
devices_lock = asyncio.Lock()


async def add_device(device) -> None:
    """Add a device to the list with thread-safe locking."""
    async with devices_lock:
        # Check if device already exists
        for existing in devices:
            if existing.uuid == device.uuid:
                return  # Already exists
        devices.append(device)


async def remove_device(uuid: str) -> bool:
    """Remove a device by UUID with thread-safe locking."""
    async with devices_lock:
        for i, device in enumerate(devices):
            if device.uuid == uuid:
                devices.pop(i)
                return True
        return False


def as_text(value, default=""):
    extracted = extract_value(value, default)
    if extracted is None:
        return default
    return str(extracted)


class DlnaDeviceService(object):

    def __init__(self, service_dict: dict, device):
        self.service_type = as_text(service_dict.get('serviceType'))
        control_url = as_text(service_dict.get('controlURL'))
        event_url = as_text(service_dict.get('eventSubURL'))
        spec_url = as_text(service_dict.get('SCPDURL'))
        self.control_url = urljoin(device.location_url, control_url)
        self.event_url = urljoin(device.location_url, event_url)
        self.spec_url = urljoin(device.location_url, spec_url)
        self.urn = self.service_type
        self.device = device
        self.subscribed = False
        self._spec_info = None
        self.next_subscribe_call_time = None

    def payload_from_template(self, action: str, data: dict):
        fields = ''
        for tag, value in data.items():
            # XML-escape values to handle & and other special chars in URLs
            escaped_value = xml_escape(as_text(value))
            fields += '<{tag}>{value}</{tag}>'.format(tag=tag, value=escaped_value)
        payload = PAYLOAD_FMT.format(action=action, urn=self.urn, fields=fields)
        return payload

    async def control(self, action: str, data: dict, client: aiohttp.ClientSession = None):
        headers = {
            'Content-type': 'text/xml',
            'SOAPACTION': '"{}#{}"'.format(self.urn, action),
            'charset': 'utf-8',
            'User-Agent': '{}/{}'.format(__file__, '1.0')
        }
        if client is None:
            client = g.http
        action_spec = await self.get_action_spec(action, client=client)
        if action_spec is None:
            raise Exception(f"No such action {action}, {self.service_type}")

        if action_spec.argumentList.argument:
            args = []
            if isinstance(action_spec.argumentList.argument, list):
                args = action_spec.argumentList.argument
            else:
                args = [action_spec.argumentList.argument]
            if not isinstance(data, dict):
                none_default_arguments = []
                for argument in args:
                    arg_name = as_text(getattr(argument, 'name', None))
                    if arg_name not in DEFAULT_ACTION_DATA.keys():
                        none_default_arguments.append(argument)
                if len(none_default_arguments) == 1:
                    data = {as_text(getattr(none_default_arguments[0], 'name', None)): data}
                elif len(none_default_arguments) != 0:
                    raise Exception(f"{action} needs {len(none_default_arguments)} arguments, pass data as dict.")
            for argument in args:
                arg_name = as_text(getattr(argument, 'name', None))
                if arg_name in DEFAULT_ACTION_DATA.keys() and arg_name not in data.keys():
                    data[arg_name] = DEFAULT_ACTION_DATA[arg_name]
        payload = self.payload_from_template(action, data)

        last_exception = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with client.post(self.control_url, data=payload.encode('utf8'), headers=headers, timeout=5) as response:
                    # Check for 5xx errors that should be retried
                    if 500 <= response.status < 600:
                        raise ServerErrorException(response.status, await response.text())
                    # 4xx and other errors still raise immediately
                    if not response.ok:
                        raise Exception(f"service {self.control_url} {action} {response.status} {await response.text()}")
                    self.device.repeat_error_count = 0
                    
                    # Get response, sanitize for device quirks, parse defensively
                    response_text = await response.text()
                    sanitized = sanitize_soap_response(response_text)
                    if sanitized != response_text:
                        logger.debug("dlna %s %s sanitized malformed XML response", self.device.name, action)
                    
                    try:
                        info = xml2dict(sanitized)
                    except Exception as parse_error:
                        logger.warning("dlna %s %s XML parse error: %s", self.device.name, action, str(parse_error))
                        return None
                    
                    error = info.Envelope.Body.Fault.detail.UPnPError.get('errorDescription')
                    if error is not None:
                        logger.warning("dlna device control request error: %s", info.toDict())
                        return None
                    return info.Envelope.Body.get(f"{action}Response")
            except ClientConnectionError as e:
                last_exception = e
                if attempt < MAX_RETRIES:
                    logger.debug("dlna %s %s connection error (attempt %d/%d), retrying: %s", 
                                self.device.name, action, attempt, MAX_RETRIES, str(e))
                    continue
                # All retries exhausted
                logger.warning("dlna %s %s connection failed after %d attempts: %s",
                              self.device.name, action, MAX_RETRIES, str(e))
                self.device.repeat_error_count += 1
                if self.device.repeat_error_count >= ERROR_COUNT_TO_REMOVE:
                    logger.warning("remove device %s due to %d connection errors", self.device.name, self.device.repeat_error_count)
                    if asyncio.get_running_loop() == self.device.loop:
                        asyncio.create_task(self.device.remove_self())
                    else:
                        asyncio.run_coroutine_threadsafe(self.device.remove_self(), self.device.loop)
                raise
            except ServerErrorException as e:
                if attempt < MAX_RETRIES:
                    logger.debug("dlna %s %s server error %d (attempt %d/%d), retrying",
                                self.device.name, action, e.status, attempt, MAX_RETRIES)
                    continue
                logger.warning("dlna %s %s server error %d after %d attempts",
                              self.device.name, action, e.status, MAX_RETRIES)
                raise
            except Exception as e:
                # Non-connection errors: don't retry, just raise
                logger.error("dlna %s %s control error %s: %s", self.device.name, action, e.__class__.__name__, str(e))
                if "different loop" in str(e):
                    traceback.print_tb(e.__traceback__)
                raise

    async def subscribe(self, timeout_sec=None):
        if timeout_sec is None:
            timeout_sec = settings.dlna_subscribe_timeout
        if settings.host_ip is None:
            settings.host_ip = guess_local_ip()
        if settings.host_ip in (None, "0.0.0.0"):
            logger.warning("dlna subscribe no host ip")
            return False
        if self.next_subscribe_call_time is not None:
            if datetime.now(timezone.utc) < self.next_subscribe_call_time:
                return
        headers = {
            'Cache-Control': 'no-cache',
            'User-Agent': '{}/{}'.format(__file__, '1.0'),
            'NT': 'upnp:event',
            'Callback': '<http://' + settings.host_ip + ':' + str(settings.http_port) + '/dlna/callback/'
                        + self.device.uuid + '>',
            'Timeout': f'Second-{timeout_sec}'
        }
        logger.info("sub dlna device %s %s", self.device.name, self.service_type)
        async with g.http.request("SUBSCRIBE", self.event_url, headers=headers) as response:
            if response.ok:
                self.next_subscribe_call_time = datetime.now(timezone.utc) + timedelta(seconds=(timeout_sec // 2))
                return True
        return False

    async def get_spec(self, client: aiohttp.ClientSession = None):
        if self._spec_info is not None:
            return self._spec_info
        if client is None:
            client = g.http
        async with client.get(self.spec_url) as response:
            response.raise_for_status()
            xml = re.sub(" xmlns=\"[^\"]+\"", "", await response.text(), count=1)
            info = xml2dict(xml)
            self._spec_info = info
        return self._spec_info

    async def get_actions(self, client: aiohttp.ClientSession = None):
        spec = await self.get_spec(client=client)
        actions = spec['scpd']['actionList']['action']
        if not isinstance(actions, (list, tuple)):
            actions = [actions]
        return actions

    async def get_action_spec(self, action_name, client: aiohttp.ClientSession = None):
        for action in await self.get_actions(client=client):
            if as_text(action.get('name')) == action_name:
                return action
        return None

    async def get_state_variables(self):
        spec = await self.get_spec()
        vars = spec['scpd']['serviceStateTable']['stateVariable']
        if not isinstance(vars, (list, tuple)):
            vars = [vars]
        return vars


class DlnaDevice(object):

    def __init__(self, location_url):
        self.location_url = location_url
        self.name = None
        self.model = None
        self.ip = None
        self.info = None
        self.services = {}
        self.volume_max = None
        self.volume_min = None
        self.volume_step = None
        self.uuid = None
        self.loop = asyncio.get_running_loop()
        self.repeat_error_count = 0

    async def get_data(self):
        if self.info is None:
            async with g.http.get(self.location_url) as response:
                if response.ok:
                    xml = await response.text()
                    xml = re.sub(" xmlns=\"[^\"]+\"", "", xml, count=1)
                    info = xml2dict(xml)
                    info = info['root']
                    self.info = info
            if self.info:
                device_info = self.info['device']
                self.name = as_text(device_info.get('friendlyName'))
                model_desc = device_info.get('modelDescription', settings.product)
                self.model = as_text(model_desc, settings.product)
                udn = as_text(device_info.get('UDN'))
                if udn.startswith("uuid:"):
                    udn = udn[len("uuid:"):]
                self.uuid = udn
                self.services = {}
                renderer_name = None

                def register_service(service, source_device=None):
                    nonlocal renderer_name
                    service_type = as_text(service.get('serviceType'))
                    if not service_type:
                        return
                    normalized_type = service_type
                    service_lc = service_type.lower()
                    if service_lc.startswith("urn:schemas-upnp-org:service:avtransport:"):
                        normalized_type = UPNP_AVT_SERVICE_TYPE
                        if renderer_name is None and source_device is not None:
                            renderer_name = as_text(source_device.get('friendlyName')) or renderer_name
                    elif service_lc.startswith("urn:schemas-upnp-org:service:renderingcontrol:"):
                        normalized_type = UPNP_RC_SERVICE_TYPE
                    if normalized_type not in self.services:
                        self.services[normalized_type] = DlnaDeviceService(service, self)

                def walk_device(dev_section):
                    service_block = dev_section.get('serviceList', {})
                    service_list = service_block.get('service', [])
                    if service_list is None:
                        service_list = []
                    if not isinstance(service_list, (list, tuple)):
                        service_list = [service_list]
                    for service in service_list:
                        if service:
                            register_service(service, source_device=dev_section)
                    device_block = dev_section.get('deviceList', {})
                    child_devices = device_block.get('device', [])
                    if child_devices is None:
                        child_devices = []
                    if not isinstance(child_devices, (list, tuple)):
                        child_devices = [child_devices]
                    for child in child_devices:
                        if child:
                            walk_device(child)

                walk_device(device_info)
                if renderer_name and renderer_name.lower() != (self.name or '').lower():
                    self.name = renderer_name
            if not self.name or not self.uuid:
                raise Exception(f"not valid dlna device {self.location_url}")
            if UPNP_AVT_SERVICE_TYPE not in self.services or UPNP_RC_SERVICE_TYPE not in self.services:
                logger.warning("dlna device %s missing required services: %s", self.name, list(self.services.keys()))
                raise Exception(f"not valid dlna device {self.name}")
            url = urlparse(self.location_url)
            self.ip = url.hostname
            self.name = settings.dlna_name_alias(self.uuid, self.name, self.ip)
            await self.get_volume_info()
            await asyncio.gather(*[s.get_spec() for s in self.services.values()])

    async def _find_service_by_action(self, action):
        await self.get_data()
        for t, service in self.services.items():
            a = await service.get_action_spec(action)
            if a is not None:
                return service
        return None

    def __getattr__(self, item):
        def action(data: dict = {}, client: aiohttp.ClientSession = None):
            return self.action(item, data=data, client=client)
        return action

    async def action(self, action: str, data: dict = {}, service_type: str = None, client: aiohttp.ClientSession = None):
        await self.get_data()
        service = None
        if service_type is not None:
            service = self._get_service(service_type)
            if service is None:
                raise Exception(f"service type not found {service_type}")
        else:
            service = await self._find_service_by_action(action)
            if service is None:
                raise Exception(f"action not found {action}")
        return await service.control(action, data, client=client)

    def _get_service(self, service_type: str):
        return self.services.get(service_type)

    async def subscribe(self, service_type: str = UPNP_AVT_SERVICE_TYPE, timeout_sec=120):
        await self.get_data()
        service = self._get_service(service_type)
        await service.subscribe(timeout_sec=timeout_sec)

    async def loop_subscribe(self, service_type: str = UPNP_AVT_SERVICE_TYPE, timeout_sec=120):
        service = self._get_service(service_type)
        if service.subscribed:
            return
        service.subscribed = True
        while service.subscribed:
            try:
                await self.subscribe(service_type=service_type, timeout_sec=timeout_sec)
                await asyncio.sleep(timeout_sec // 2)
            except ClientConnectorError as exc:
                logger.warning("dlna %s subscribe loop connection error: %s", self.name, exc)
                if not service.subscribed:
                    break
                await asyncio.sleep(min(timeout_sec, 15))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("dlna %s subscribe loop error: %s", self.name, exc)
                if not service.subscribed:
                    break
                await asyncio.sleep(min(timeout_sec, 10))

    def stop_subscribe(self, service_type: str = UPNP_AVT_SERVICE_TYPE):
        service = self._get_service(service_type)
        if service:
            service.subscribed = False

    async def get_volume_info(self):
        await self.get_data()
        self.volume_min = 0
        self.volume_max = 100
        self.volume_step = 1
        service = self._get_service(UPNP_RC_SERVICE_TYPE)
        try:
            vars = await service.get_state_variables()
            for v in vars:
                if as_text(v.get('name')) == "Volume":
                    r = v.get('allowedValueRange')
                    if not r:
                        continue
                    self.volume_min = int(as_text(r.get('minimum'), 0))
                    self.volume_max = int(as_text(r.get('maximum'), 100))
                    self.volume_step = int(as_text(r.get('step'), 1))
                    break
        except Exception:
            logger.exception("Unexpected error parsing volume range")

    async def remove_self(self):
        devices.remove(self)
        from plex.adapters import adapter_by_device, remove_adapter
        from plex.subscribe import sub_man
        self.stop_subscribe()
        adapter = await adapter_by_device(self)
        adapter.state.state = "STOPPED"
        adapter.state._wakeup_loop()
        adapter.state._thread_should_stop = True
        await sub_man.notify_device_disconnected(self)
        await sub_man.notify_server_device(self, force=True)
        adapter.queue = None
        remove_adapter(adapter)
        settings.mark_device_status(self.uuid, "offline")

    def __str__(self):
        return self.name

    def __repr__(self):
        return " ".join(["DLNA Device", self.name, self.ip])

    def __eq__(self, other):
        return self.uuid == other.uuid


# if settings.location_url is not None:
#     devices.append(DlnaDevice(settings.location_url))


async def get_device_data():
    async with devices_lock:
        device_list = list(devices)
    await asyncio.gather(*[device.get_data() for device in device_list])


async def get_device_by_uuid(uuid):
    async with devices_lock:
        for device in devices:
            if device.uuid == uuid:
                # Release lock before async operation
                break
        else:
            device = None
    
    if device is not None:
        await device.get_data()
        return device
    
    # Fallback to virtual devices
    try:
        from dlna.virtual import get_virtual_device_by_uuid

        virtual_device = await get_virtual_device_by_uuid(uuid)
        if virtual_device is not None:
            return virtual_device
    except Exception:
        # Avoid breaking physical device lookup if virtual module fails
        pass
    logger.debug("device uuid not found: %s", uuid)
    return None
