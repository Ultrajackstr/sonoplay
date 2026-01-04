# SPDX-License-Identifier: GPL-3.0-or-later
#
# Original work Copyright (C) 2021 songchenwen
# Modified work Copyright (C) 2025 plexdlnaplayer-enhanced contributors
#
# This file is part of plexdlnaplayer-enhanced, a fork of plexdlnaplayer.
# Original project: https://github.com/songchenwen/plexdlnaplayer
#
# Modifications from original:
#   - Added virtual device support and fan-out orchestration
#   - Enhanced state management with operation-in-progress protection
#   - Added transport operation debouncing for Sonos compatibility
#   - Improved error handling and timeout management
#   - Added timezone-aware datetime handling
#   - Extended metadata extraction for enhanced UI
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import asyncio
from datetime import timedelta, datetime, timezone
import math
import random
import time
from threading import Thread, current_thread
import weakref
from typing import TYPE_CHECKING, Optional

import aiohttp
from dotmap import DotMap
from starlette.datastructures import QueryParams

from plex.play_queue import PlayQueue
from utils import parse_timedelta, convert_volume, g, pms_header, extract_value
from settings import settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from dlna.virtual.devices import VirtualDlnaDevice

adapters = {}


def adapter_by_device(device, query_params: QueryParams = None):
    a = adapters.get(device.uuid, None)
    if a is None:
        a = PlexDlnaAdapter(device, query_params)
        adapters[device.uuid] = a
    elif query_params is not None:
        a.plex_lib.update(query_params)
    return a


def remove_adapter(adapter):
    """Remove an adapter and clean up its resources."""
    if adapter.dlna.uuid in adapters:
        # Shutdown the state thread before removing
        if hasattr(adapter, 'state') and adapter.state is not None:
            adapter.state.shutdown()
        del adapters[adapter.dlna.uuid]


class PlexLib(object):

    def __init__(self):
        self.protocol = ''
        self.address = ''
        self.port = ''
        self.token = ''
        self.machine_id = ''
        self.client_identifier = ''
        self.device = None

    def build_url(self, resource, token=True):
        url = f"{self.protocol}://{self.address}:{self.port}{resource}"
        if token:
            if "?" in resource:
                url += f"&X-Plex-Token={self.token}"
            else:
                url += f"?X-Plex-Token={self.token}"
        return url

    def update(self, query: QueryParams):
        if query is None:
            return
        self.protocol = query.get("protocol", self.protocol)
        self.address = query.get("address", self.address)
        self.port = int(query.get("port", self.port))
        self.token = query.get("token", self.token)
        self.machine_id = query.get("machineIdentifier", self.machine_id)
        self.client_identifier = query.get("clientIdentifier", self.client_identifier)

    def request_headers(self, *, accept_json: bool = False) -> dict:
        headers = {}
        if accept_json:
            headers["Accept"] = "application/json"
        client_identifier = self.client_identifier or getattr(self.device, "uuid", None) or self.machine_id
        if client_identifier:
            headers["X-Plex-Client-Identifier"] = client_identifier
        product = getattr(settings, "product", None)
        if product:
            headers.setdefault("X-Plex-Product", product)
        version = getattr(settings, "version", None)
        if version:
            headers.setdefault("X-Plex-Version", version)
        platform = getattr(settings, "platform", None)
        if platform:
            headers.setdefault("X-Plex-Platform", platform)
        platform_version = getattr(settings, "platform_version", None)
        if platform_version:
            headers.setdefault("X-Plex-Platform-Version", platform_version)
        device_name = getattr(self.device, "name", None) or getattr(settings, "client_device_name", None) or product
        if device_name:
            headers.setdefault("X-Plex-Device-Name", device_name)
        descriptor = getattr(settings, "client_model", None) or getattr(self.device, "model", None) or getattr(self.device, "name", None) or product
        device_header = getattr(settings, "client_device", None) or descriptor
        if device_header:
            headers.setdefault("X-Plex-Device", device_header)
        if descriptor:
            headers.setdefault("X-Plex-Model", descriptor)
        client_profile = getattr(settings, "client_profile", None)
        if client_profile:
            headers.setdefault("X-Plex-Client-Profile-Name", client_profile)
        headers.setdefault("X-Plex-Provides", "player,pubsub-player")
        return headers

    def get_info(self):
        return dict(protocol=self.protocol,
                    address=self.address,
                    port=self.port,
                    machineIdentifier=self.machine_id)

    def get_queue(self, container_key):
        return PlayQueue(container_key, self)

    def get_timeline(self):
        return self.build_url("/:/timeline", token=False)


class DlnaState(object):
    changing_attrs = ("state", "volume", "elapsed", "current_uri", "current_track_duration", "muted")

    def __init__(self, adapter, state_change_callback=None):
        self.adapter = adapter
        self.dlna = adapter.dlna
        self._state = None
        self._volume = None
        self._elapsed = 0
        self._current_uri = None
        self._current_track_duration = None
        self._muted = None

        self.looping_thread: Thread = None
        self._thread_should_stop = False
        self.running_loop: asyncio.AbstractEventLoop = None
        self.state_change_callback = state_change_callback
        self._changed_state = None
        self.change_session_lock = None
        self._check_all_next_loop = False
        self.looping_wait_event: asyncio.Event = None
        self.last_access_time = datetime.now(timezone.utc)
        self.start_looping()

    def start_looping(self):
        if self.looping_thread is not None and self.looping_thread.is_alive():
            return
        if self.looping_thread is not None and not self.looping_thread.is_alive():
            try:
                self.looping_thread.join(timeout=0)
            except Exception:
                pass
            print(f"{self.dlna} state restarting loop thread")
        self._thread_should_stop = False
        self.running_loop = None
        self.looping_wait_event = None
        self.change_session_lock = None
        print(f"{self.dlna} state start looping")
        loop_thread = Thread(target=self.background_loop,
                              name=f"Dlna State Thread {str(self.dlna)}")
        loop_thread.start()
        self.looping_thread = loop_thread

    def background_loop(self):
        self.running_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.running_loop)
        self.running_loop.run_until_complete(self._check_loop())

    def begin_change_session(self):
        self._changed_state = DotMap()

    def end_change_session(self):
        s = self._changed_state
        self._changed_state = None
        return s

    def _wakeup_loop(self):
        loop = self.running_loop
        event = self.looping_wait_event
        if loop is None or event is None:
            return
        if loop.is_closed():
            return
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        if current_loop is loop:
            event.set()
        elif loop.is_running():
            loop.call_soon_threadsafe(event.set)

    @property
    def check_all_next_loop(self):
        return self._check_all_next_loop

    @check_all_next_loop.setter
    def check_all_next_loop(self, value: bool):
        if self._check_all_next_loop == value:
            return
        self._check_all_next_loop = value
        if value:
            self._wakeup_loop()

    def __setattr__(self, key, value):
        if key in DlnaState.changing_attrs:
            old_value = self.__getattr__("_" + key)
            if old_value != value and self._changed_state is not None:
                self._changed_state[key] = value
                self._changed_state.old[key] = old_value
            object.__setattr__(self, "_" + key, value)
        else:
            object.__setattr__(self, key, value)

    def __getattr__(self, item):
        if item in DlnaState.changing_attrs:
            self.last_access_time = datetime.now(timezone.utc)
            self._wakeup_loop()
            return object.__getattribute__(self, "_" + item)
        return object.__getattribute__(self, item)

    def __del__(self):
        self._thread_should_stop = True
        if self.looping_thread is not None:
            if self.looping_thread.is_alive():
                self.looping_thread.join()
            self.looping_thread = None

    def shutdown(self):
        """Cleanly stop the background polling thread.
        
        This method is idempotent - safe to call multiple times.
        Wakes any sleeping thread to ensure prompt shutdown.
        """
        if self._thread_should_stop:
            return  # Already shutting down
            
        self._thread_should_stop = True
        
        # Wake the thread if it's sleeping
        running_loop = getattr(self, "running_loop", None)
        looping_event = getattr(self, "looping_wait_event", None)
        
        if running_loop is not None and not running_loop.is_closed():
            def _wake():
                if looping_event is not None:
                    looping_event.set()
            try:
                running_loop.call_soon_threadsafe(_wake)
            except RuntimeError:
                # Loop already closed
                pass
        elif looping_event is not None:
            looping_event.set()
        
        # Wait for thread to finish
        if self.looping_thread is not None and self.looping_thread.is_alive():
            self.looping_thread.join(timeout=2.0)

    def __repr__(self):
        return f"{self.dlna.name}: state {self.state} {self.elapsed} {self.volume} " \
               f"{self.muted} {self.current_track_duration} {self.current_uri}"

    async def check(self, client: aiohttp.ClientSession, check_count=0):
        position_check_count = 1
        volume_check_count = 12
        state_check_count = 10
        muted_check_count = 51
        checks = []
        results = []
        position_info = DotMap()
        state = DotMap()
        volume = DotMap()
        muted = DotMap()
        if check_count % position_check_count == 0 or self.check_all_next_loop:
            checks.append(self.dlna.GetPositionInfo(client=client))
            results.append(position_info)
        if check_count % state_check_count == 0 or self.state == "TRANSITIONING" or self.check_all_next_loop:
            checks.append(self.dlna.GetTransportInfo(client=client))
            results.append(state)
        if check_count % volume_check_count == 0 or self.check_all_next_loop:
            checks.append(self.dlna.GetVolume(client=client))
            results.append(volume)
        if check_count % muted_check_count == 0:
            checks.append(self.dlna.GetMute(client=client))
            results.append(muted)
        if self.check_all_next_loop:
            self.check_all_next_loop = False
        try:
            for idx, r in enumerate(await asyncio.gather(*checks)):
                results[idx].result = r
        except Exception as e:
            if __debug__:
                print(f"dlna {self.dlna.name} state loop error {str(e)}")
        self.begin_change_session()
        if position_info and position_info.result:
            position_info = position_info.result
            self.elapsed = int(parse_timedelta(position_info.RelTime).total_seconds() * 1000)
            self.current_uri = position_info.TrackURI
            self.current_track_duration = int(
                parse_timedelta(position_info.TrackDuration).total_seconds() * 1000)
            if not state and not self._changed_state and self.state in ("TRANSITIONING", "PLAYING"):
                if __debug__:
                    print(f"dlna {self.dlna.name} no eplased change? retry state")
                try:
                    state.result = await self.dlna.GetTransportInfo(client=client)
                except Exception:
                    pass
        if state and state.result:
            state = state.result
            self.state = state.CurrentTransportState
        if volume and volume.result:
            volume_info = volume.result
            volume_value = extract_value(getattr(volume_info, 'CurrentVolume', None))
            try:
                volume_value = int(volume_value)
            except (TypeError, ValueError):
                volume_value = self.dlna.volume_min
            self.volume = convert_volume(volume_value, self.dlna.volume_max, self.dlna.volume_min, 100, 0, 1)
        if muted and muted.result:
            muted_info = muted.result
            muted_value = extract_value(getattr(muted_info, 'CurrentMute', None))
            if isinstance(muted_value, str):
                muted_value = muted_value.lower() in ("1", "true", "yes")
            self.muted = bool(muted_value)
        changed_state = self.end_change_session()
        if changed_state and self.state_change_callback:
            # if __debug__:
            #     print(f"{self.dlna.name} check loop {changed_state.toDict()} {self} in thread {current_thread().name}")
            self.state_change_callback(changed_state)

    @property
    def loop_interval(self):
        if datetime.now(timezone.utc) - self.last_access_time >= timedelta(seconds=90) \
                and self.state not in ("PLAYING", "TRANSITIONING"):
            return settings.adapter_idle_interval
        return 0.8

    async def wait_for_next_loop(self):
        try:
            await asyncio.wait_for(self.looping_wait_event.wait(), timeout=self.loop_interval)
        except Exception:
            pass
        self.looping_wait_event.clear()

    async def _check_loop(self):
        print(f"state loop {self.dlna.name} begin in {current_thread().name}")
        if self.change_session_lock is None:
            self.change_session_lock = asyncio.Lock()
        if self.looping_wait_event is None:
            self.looping_wait_event = asyncio.Event()
        async with aiohttp.ClientSession() as client:
            check_count = 0
            one_batch_count = 500
            while not self._thread_should_stop:
                async with self.change_session_lock:
                    await self.check(client, check_count=check_count)
                check_count += 1
                if check_count > one_batch_count:
                    check_count = 0
                await self.wait_for_next_loop()
        print(f"{self.dlna.name} state loop {self.dlna.name} stopped")
        self.running_loop = None

    def update(self, state: str = "", uri: str = "", position: str = ""):
        elapsed = ""
        if position:
            elapsed = int(parse_timedelta(position).total_seconds() * 1000)
        if (state == "" or self.state == state) and (uri == "" or self.current_uri == uri) and (elapsed == "" or self.elapsed == elapsed):
            return
        loop_obj = self.running_loop
        loop_alive = self.looping_thread is not None and self.looping_thread.is_alive()
        loop_ready = loop_alive and loop_obj is not None and not loop_obj.is_closed()
        if not loop_ready:
            self.start_looping()
            self._apply_update_without_loop(state=state, uri=uri, elapsed=elapsed)
            return
        if current_thread() == self.looping_thread:
            loop_obj.create_task(self.update_in_thread(state=state, uri=uri, elapsed=elapsed))
        else:
            asyncio.run_coroutine_threadsafe(self.update_in_thread(state=state, uri=uri, elapsed=elapsed),
                                             loop_obj)

    async def update_in_thread(self, state="", uri="", elapsed=""):
        if state == "":
            state = self.state
        if uri == "":
            uri = self.current_uri
        if elapsed == "":
            elapsed = self.elapsed
        if self.state == state and self.current_uri == uri and self.elapsed == elapsed:
            return
        if __debug__:
            print(f"{self.dlna.name} real update state from sub {state} {uri} {elapsed}")
        async with self.change_session_lock:
            if __debug__:
                print(f"{self.dlna.name} real update state from sub in lock {state} {uri} {elapsed}")
            self.begin_change_session()
            self.state = state
            self.current_uri = uri
            self.elapsed = elapsed
            changed = self.end_change_session()
            if changed and self.state_change_callback:
                self.state_change_callback(changed)

    def _apply_update_without_loop(self, state: str = "", uri: str = "", elapsed="") -> None:
        if state == "":
            state = self.state
        if uri == "":
            uri = self.current_uri
        if elapsed == "":
            elapsed = self.elapsed
        if self.state == state and self.current_uri == uri and self.elapsed == elapsed:
            return
        if __debug__:
            print(f"{self.dlna.name} applying state update without loop {state} {uri} {elapsed}")
        self.begin_change_session()
        self.state = state
        self.current_uri = uri
        self.elapsed = elapsed
        changed = self.end_change_session()
        if changed and self.state_change_callback:
            self.state_change_callback(changed)


class PlexDlnaAdapter(object):

    def __init__(self, dlna, query: QueryParams = None):
        print(f"init adapter for {dlna} in thread {current_thread().name}")
        self.dlna = dlna
        self.plex_lib = PlexLib()
        self.plex_lib.device = self.dlna
        if query is not None:
            self.plex_lib.update(query)
        if not self.plex_lib.client_identifier:
            self.plex_lib.client_identifier = self.dlna.uuid
        self.queue = None
        self.state: DlnaState = DlnaState(self, self.state_changed_callback)
        self.shuffle = 0
        self.plex_bind_token = settings.get_token_for_uuid(self.dlna.uuid)
        self.no_notice = False
        self.loop = asyncio.get_running_loop()
        self.wait_state_change_events = []
        self.delay_stop_state_looping_task: asyncio.Task = None
        self.waiting_sub = 0
        self.current_track_info = None
        stored_stats = settings.get_device_stats(self.dlna.uuid)
        self.stats_play_count = stored_stats.get('play_count', 0)
        self.stats_play_duration_ms = stored_stats.get('play_duration_ms', 0)
        self.stats_session_start: datetime = None
        # Flag to track if this device is being controlled by a virtual device
        self._controlled_by_virtual_device = False
        self._virtual_controller_ref: Optional[weakref.ReferenceType] = None
        self._transport_lock = asyncio.Lock()
        self._operation_sequence = 0
        self._active_operation_id = 0
        self._active_target_uri: Optional[str] = None
        self._active_operation_event: Optional[asyncio.Event] = None
        self._active_operation_uri_confirmed = False
        self._active_operation_state_ready = False
        self._active_operation_state_confirmed = False
        self._active_operation_target_paused = False
        self._transport_state_override: Optional[dict] = None
        self._transport_settle_timeout = 6.0
        self._transport_max_attempts = 3
        self._suppress_auto_next = False
        self._last_operation_finish_time: Optional[float] = None
        self._post_operation_protection_window = 2.0  # seconds
        self._last_finished_target_uri: Optional[str] = None

    def _start_transport_operation(self, target_uri: str) -> int:
        self._operation_sequence += 1
        self._active_operation_id = self._operation_sequence
        self._active_target_uri = target_uri
        self._active_operation_event = asyncio.Event()
        self._active_operation_uri_confirmed = False
        self._active_operation_state_ready = False
        self._active_operation_state_confirmed = False
        self._active_operation_target_paused = False
        self._transport_state_override = {
            "state": "TRANSITIONING",
            "current_uri": target_uri
        }
        self._suppress_auto_next = False
        print(f"{self.dlna.name} transport operation {self._active_operation_id} started for {target_uri}")
        return self._active_operation_id

    def _finish_transport_operation(self, operation_id: int) -> None:
        if self._active_operation_id != operation_id:
            return
        print(f"{self.dlna.name} transport operation {operation_id} finished")
        # Record finish time and URI for post-operation protection
        self._last_operation_finish_time = time.monotonic()
        self._last_finished_target_uri = self._active_target_uri
        # Clear active operation state
        self._active_operation_id = 0
        self._active_target_uri = None
        self._active_operation_event = None
        self._active_operation_uri_confirmed = False
        self._active_operation_state_ready = False
        self._active_operation_state_confirmed = False
        self._active_operation_target_paused = False
        self._transport_state_override = None

    def _check_post_operation_false_stop(self, changed_state: DotMap) -> bool:
        """
        Detect and recover from spurious STOPPED state immediately after transport operation.
        
        Sonos devices sometimes report PLAYING briefly, then STOPPED, causing playback
        to get stuck. This method detects when:
        1. State changed from PLAYING to STOPPED
        2. We recently finished a transport operation (within protection window)
        3. The track just started (elapsed is very low)
        
        When detected, it triggers a retry of the current track.
        Returns True if false stop was detected and handled, False otherwise.
        """
        # Only check for PLAYING -> STOPPED transitions
        if 'state' not in changed_state:
            return False
        if changed_state.state != "STOPPED":
            return False
        if changed_state.old.get('state') != "PLAYING":
            return False
        
        # Check if we're within the post-operation protection window
        if self._last_operation_finish_time is None:
            return False
        
        time_since_finish = time.monotonic() - self._last_operation_finish_time
        if time_since_finish > self._post_operation_protection_window:
            return False
        
        # Check if track just started (elapsed is low, indicating false stop not natural end)
        elapsed = self.state.elapsed if hasattr(self.state, 'elapsed') else 0
        duration = self.state.current_track_duration if hasattr(self.state, 'current_track_duration') else 0
        
        # If elapsed is more than 5 seconds and track is substantial, this might be legitimate
        # (though still suspicious if within protection window)
        if elapsed > 5000 and duration > 0 and (duration - elapsed) > 5000:
            return False
        
        print(f"{self.dlna.name} detected false STOP {time_since_finish:.2f}s after transport operation "
              f"(elapsed={elapsed}ms, duration={duration}ms), triggering recovery")
        
        # Clear the finish time to prevent infinite retry loops
        self._last_operation_finish_time = None
        
        # Suppress auto-next during recovery
        self._suppress_auto_next = True
        
        # Schedule recovery: replay the current track
        async def recover_playback():
            try:
                if self.queue is not None:
                    print(f"{self.dlna.name} recovery: replaying current track")
                    await self.play_selected_queue_item()
                else:
                    print(f"{self.dlna.name} recovery: no queue, cannot replay")
            finally:
                self._suppress_auto_next = False
        
        asyncio.run_coroutine_threadsafe(recover_playback(), self.loop)
        return True

    def attach_virtual_controller(self, controller: "VirtualDlnaDevice") -> None:
        self._virtual_controller_ref = weakref.ref(controller)
        self._controlled_by_virtual_device = True

    def detach_virtual_controller(self, controller: "VirtualDlnaDevice") -> None:
        if self._virtual_controller_ref is None:
            return
        current = self._virtual_controller_ref()
        if current is controller:
            self._virtual_controller_ref = None
            self._controlled_by_virtual_device = False

    def virtual_controller(self) -> Optional["VirtualDlnaDevice"]:
        if self._virtual_controller_ref is None:
            return None
        return self._virtual_controller_ref()

    def check_auto_next(self, changed: DotMap):
        # Skip auto-next logic when a virtual device is orchestrating playback for this member
        if self._controlled_by_virtual_device:
            return False
        if self._suppress_auto_next:
            return False
        if self._active_operation_id:
            return False
        if self.queue is None:
            return False
        if changed.state and changed.state != "PLAYING" and changed.old.state == "TRANSITIONING":
            return False

        async def auto_next():
            if self.queue.repeat == 1:
                await self.play_selected_queue_item()
            elif self.queue.repeat == 2 and \
                    (await self.queue.selected_offset()) >= (await self.queue.total_count() - 1) and \
                    self.shuffle == 0:
                await self.queue.set_selected_offset(0)
                await self.play_selected_queue_item()
            else:
                await self.next()

        if self.state.current_uri is not None and not changed.state and not changed.uri and self.current_track_info:
            if (changed.elapsed == 0 < changed.old.elapsed <= self.current_track_info.duration
                and self.current_track_info.duration - changed.old.elapsed <= 2000) \
                    or (
                    changed.elapsed and changed.elapsed > changed.old.elapsed and
                    self.current_track_info.duration // 1000 * 1000 <= changed.elapsed <= self.current_track_info.duration):
                self.no_notice = True
                print(f"auto next stopped {self.state.state}, elapsed: {changed.old.elapsed} -> {changed.elapsed}, "
                      f"{self.current_track_info.duration}")
                self.state.update(state="TRANSITIONING", uri=None)
                asyncio.run_coroutine_threadsafe(auto_next(), self.loop)
                self.no_notice = False
                return True
        elif not changed.uri and changed.old.state == "PLAYING" and changed.state == "STOPPED" and self.state.current_track_duration - self.state.elapsed <= 1:
            self.no_notice = True
            print(f"auto next transitioning {changed.old.state} {changed.state}")
            self.state.update(state="TRANSITIONING", uri=None)
            asyncio.run_coroutine_threadsafe(auto_next(), self.loop)
            self.no_notice = False
            return True
        return False

    def state_changed_callback(self, changed_state: DotMap):
        if self.loop.is_closed():
            return
        if __debug__ or 'elapsed' not in changed_state.keys() or len(changed_state.keys()) > 2 or \
                not (0 <= changed_state.elapsed - changed_state.old.elapsed <= 1000):
            print(f"{self.dlna.name} state change notified {changed_state.toDict()}")
        if self._active_operation_id:
            if 'current_uri' in changed_state:
                if changed_state.current_uri == self._active_target_uri:
                    self._active_operation_uri_confirmed = True
                    if self._active_operation_state_ready and not self._active_operation_state_confirmed:
                        self._active_operation_state_confirmed = True
                        if self._active_operation_event:
                            self._active_operation_event.set()
                        print(f"{self.dlna.name} transport operation {self._active_operation_id} uri confirmed")
                        self._transport_state_override = None
                elif changed_state.current_uri is None and changed_state.old.get('current_uri') == self._active_target_uri:
                    print(f"{self.dlna.name} ignoring transient URI clear during active transport operation")
                    self.state.update(uri=self._active_target_uri)
                    return
                elif changed_state.current_uri and changed_state.current_uri != self._active_target_uri:
                    if changed_state.old.get('current_uri') == self._active_target_uri:
                        # Sonos reverted from our target URI - device likely rejected it
                        # Check if current track is playable before trying to restore
                        # This is a fallback in case transcoding fails or other issues occur
                        if hasattr(self, 'current_track_info') and self.current_track_info:
                            if not self.queue.is_track_playable(self.current_track_info):
                                print(f"{self.dlna.name} device rejected track even after transcode attempt, skipping to next")
                                # Cancel the active operation and skip to next track
                                self._active_operation_id = None
                                self._active_operation_event = None
                                self._transport_state_override = None
                                # Schedule next() to run in the event loop
                                asyncio.run_coroutine_threadsafe(self.next(), self.loop)
                                return
                        print(f"{self.dlna.name} reverting URI {changed_state.current_uri} -> restoring target {self._active_target_uri}")
                        self.state.update(uri=self._active_target_uri)
                        return
                    if __debug__:
                        print(f"{self.dlna.name} received uri {changed_state.current_uri} while targeting {self._active_target_uri}")
            if 'state' in changed_state:
                if changed_state.state in ("PLAYING", "PAUSED_PLAYBACK"):
                    self._active_operation_state_ready = True
                    if self._active_operation_uri_confirmed and not self._active_operation_state_confirmed:
                        self._active_operation_state_confirmed = True
                        if self._active_operation_event:
                            self._active_operation_event.set()
                        print(f"{self.dlna.name} transport operation {self._active_operation_id} state confirmed")
                        self._transport_state_override = None
                elif changed_state.state == "STOPPED" and not self._active_operation_state_confirmed:
                    print(f"{self.dlna.name} ignoring STOP during active transport operation")
                    self.state.update(state="TRANSITIONING")
                    return
        # Post-operation protection: detect spurious STOPPED immediately after operation finish
        if self._check_post_operation_false_stop(changed_state):
            return
        n = self.check_auto_next(changed_state)
        if not n:
            asyncio.run_coroutine_threadsafe(self.state_changed(changed_state), self.loop)

    async def state_changed(self, changed_state: DotMap):
        removed_event = []
        for e in self.wait_state_change_events:
            if not e['interesting_fields']:
                e['event'].set()
                removed_event.append(e)
                continue
            for f in e['interesting_fields']:
                if f in changed_state.keys():
                    e['event'].set()
                    removed_event.append(e)
                    continue
            if "elapsed_jump" in e['interesting_fields']:
                if "elapsed" in changed_state and not (0 <= changed_state.elapsed - changed_state.old.elapsed <= 1000):
                    e['event'].set()
                    removed_event.append(e)
                    continue
        for r in removed_event:
            self.wait_state_change_events.remove(r)
        self._update_stats(changed_state)

    async def wait_for_event(self, timeout=None, interesting_fields=None):
        event = asyncio.Event()
        entry = dict(event=event, interesting_fields=interesting_fields)
        self.wait_state_change_events.append(entry)
        if len(self.wait_state_change_events) > 3:
            e = self.wait_state_change_events.pop()
            e['event'].set()
        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.exceptions.TimeoutError:
            pass
        finally:
            # Always clean up the entry, whether event was set or timed out
            if entry in self.wait_state_change_events:
                self.wait_state_change_events.remove(entry)

    def _normalize_state(self, value):
        state_value = extract_value(value)
        if isinstance(state_value, str):
            return state_value.upper()
        return None

    def _update_stats(self, changed_state: DotMap):
        # Skip stat tracking if this device is being controlled by a virtual device
        if self._controlled_by_virtual_device:
            return
            
        if 'state' not in changed_state.keys():
            return
        now = datetime.now(timezone.utc)
        current_state = self._normalize_state(self.state.state)

        if current_state == "PLAYING" and self.stats_session_start is None:
            self.stats_session_start = now
            self.stats_play_count += 1
            settings.increment_play_count(self.dlna.uuid)
        elif self.stats_session_start is not None and current_state != "PLAYING":
            elapsed = int((now - self.stats_session_start).total_seconds() * 1000)
            if elapsed > 0:
                self.stats_play_duration_ms += elapsed
                settings.add_play_duration_ms(self.dlna.uuid, elapsed)
            self.stats_session_start = None
            settings.mark_device_status(self.dlna.uuid, "online")
        else:
            status = "playing" if current_state == "PLAYING" else "online"
            settings.mark_device_status(self.dlna.uuid, status)

    def stats_snapshot(self):
        playing = self.stats_session_start is not None and self._normalize_state(self.state.state) == "PLAYING"
        current_session_ms = 0
        if playing:
            current_session_ms = int((datetime.now(timezone.utc) - self.stats_session_start).total_seconds() * 1000)
        status = "playing" if playing else "online"
        return {
            "play_count": self.stats_play_count,
            "play_duration_ms": self.stats_play_duration_ms,
            "current_session_ms": current_session_ms,
            "status": status,
            "ip": self.dlna.ip
        }

    async def play_media(self, container_key, key=None, offset=0, paused=False, query_params: QueryParams = None):
        if query_params is not None:
            self.plex_lib.update(query_params)

        controller = self.virtual_controller()
        if controller is not None:
            try:
                controller.suspend_member(self, reason="solo playback request")
                controller_adapter = adapter_by_device(controller)
                print(f"{self.dlna.name} releasing from virtual controller {controller.name} before solo playback")
                await controller_adapter.stop(force=True)
            except Exception as exc:
                print(f"{self.dlna.name} failed to stop virtual controller {controller.name}: {exc}")

        self.state.update(uri=None)
        self.queue = self.plex_lib.get_queue(container_key)
        await self.queue.get_info()
        await self.play_selected_queue_item(offset=offset, paused=paused)

    async def play_selected_queue_item(self, offset=0, paused=False):
        # Get the track to check if it needs transcoding
        track = await self.queue.selected_track()
        
        # Check if track needs transcoding due to high bitrate/sample rate
        needs_transcode = not self.queue.is_track_playable(track)
        if needs_transcode:
            title = getattr(track, 'title', 'Unknown')
            artist = getattr(track, 'grandparentTitle', 'Unknown Artist')
            media = track.Media[0] if hasattr(track, 'Media') and track.Media else None
            bitrate = getattr(media, 'bitrate', 'unknown') if media else 'unknown'
            sample_rate = getattr(media, 'audioSampleRate', 'unknown') if media else 'unknown'
            print(f"{self.dlna.name} high-bitrate track detected: '{title}' by {artist} ({bitrate} kbps, {sample_rate} Hz)")
            print(f"{self.dlna.name} using Plex transcode for Sonos compatibility")
        
        async with self._transport_lock:
            url = self.queue.url_for_track(track, force_transcode=needs_transcode)
            operation_id = self._start_transport_operation(url)
            self._active_operation_target_paused = paused
            try:
                self.current_track_info = track
                attempt = 0
                while True:
                    attempt += 1
                    if attempt > 1:
                        print(f"{self.dlna.name} retrying transport load attempt {attempt} for {url}")
                        self._reset_active_operation_tracking()
                    await self._issue_transport_commands(url, offset=offset if attempt == 1 else 0, paused=paused)
                    settled = await self._await_transport_settle(operation_id)
                    if settled or attempt >= self._transport_max_attempts:
                        if not settled:
                            print(f"{self.dlna.name} transport load timed out after {attempt} attempts for {url}")
                        break
            finally:
                self._finish_transport_operation(operation_id)
            self.current_track_info = track

    def _reset_active_operation_tracking(self) -> None:
        if not self._active_operation_id or not self._active_target_uri:
            return
        self._active_operation_event = asyncio.Event()
        self._active_operation_uri_confirmed = False
        self._active_operation_state_ready = False
        self._active_operation_state_confirmed = False
        self._transport_state_override = {
            "state": "TRANSITIONING",
            "current_uri": self._active_target_uri
        }

    async def _issue_transport_commands(self, url: str, *, offset: int, paused: bool) -> None:
        self.state.update(state="TRANSITIONING")
        self.state.check_all_next_loop = True
        if url == self.state.current_uri:
            self.state.update(uri=None)
        else:
            self.state.update(uri=url)
        await self.dlna.SetAVTransportURI(url)
        if offset != 0:
            self.state.update(position=str(timedelta(milliseconds=offset)))
            await self.dlna.Seek(str(timedelta(milliseconds=offset)))
        else:
            self.state.update(position="0")
        if paused:
            await self.pause()
        else:
            await asyncio.sleep(0.1)
            await self.play()

    async def _await_transport_settle(self, operation_id: int) -> bool:
        if self._active_operation_id != operation_id or self._active_operation_event is None:
            return True
        try:
            await asyncio.wait_for(self._active_operation_event.wait(), timeout=self._transport_settle_timeout)
            print(f"{self.dlna.name} transport operation {operation_id} settled")
        except asyncio.TimeoutError:
            print(f"{self.dlna.name} transport operation {operation_id} timed out waiting for settle")
            return False
        return self._active_operation_state_confirmed and self._active_operation_id == operation_id

    async def refresh_queue(self, playQueueID):
        await self.queue.refresh_queue(playQueueID)
        while len(self.wait_state_change_events) > 0:
            e = self.wait_state_change_events.pop()
            e['event'].set()

    async def play(self):
        await self.dlna.Play()
        self.state.check_all_next_loop = True

    async def stop(self, *, force: bool = False):
        controller = self.virtual_controller()
        if controller is not None and not force:
            print(f"{self.dlna.name} stop request rerouted to virtual device {controller.name}")
            await controller.handle_member_stop_request(self)
            return
        async with self._transport_lock:
            active_id = self._active_operation_id
            if active_id:
                self._finish_transport_operation(active_id)
            self._suppress_auto_next = True
        self.state.update(state="STOPPED", uri=None)
        self.current_track_info = None
        if force:
            self.queue = None
        await self.dlna.Stop()
        self.state.check_all_next_loop = True

    async def pause(self):
        self.state.update(state="PAUSED_PLAYBACK")
        await self.dlna.Pause()
        self.state.check_all_next_loop = True

    async def prev(self):
        if self.state.elapsed <= 5 * 1000:
            await self.next(revert=True)
        else:
            await self.seek(0)

    async def next(self, revert=False):
        direction = -1 if revert else 1
        current_offset = await self.queue.selected_offset()
        total_count = await self.queue.total_count()

        if self.shuffle > 0 and await self.queue.allow_shuffle():
            if math.isinf(total_count):
                await self.queue.get_info()
                available_count = await self.queue.available_count()
                if available_count <= 0:
                    await self.stop()
                    return
                start_offset = self.queue.start_offset or 0
                current_offset = start_offset + random.randrange(available_count)
            else:
                current_offset = random.randrange(int(total_count))
        else:
            current_offset += direction

        start_offset = self.queue.start_offset
        last_offset = self.queue.last_offset if self.queue.last_offset is not None else "unknown"
        print(f"{self.dlna.name} next diagnostics current={current_offset} last={last_offset} start={start_offset} total={total_count} direction={direction}")

        if current_offset < 0:
            print(f"{self.dlna.name} next guard stop: offset<0 current={current_offset} start={start_offset}")
            await self.stop()
            return
        if not math.isinf(total_count) and current_offset >= total_count:
            print(f"{self.dlna.name} next guard stop: offset>=total current={current_offset} total={total_count}")
            await self.stop()
            return
        self.state.update(state="TRANSITIONING")
        print(f"will play position {current_offset} of {total_count}")
        await self.queue.set_selected_offset(current_offset)
        print(f"{self.dlna.name} next invoking play_selected_queue_item offset={current_offset}")
        await self.play_selected_queue_item()

    async def skip_to_track(self, key):
        self.state.update(state="TRANSITIONING")
        await self.queue.select_track_key(key)
        await self.play_selected_queue_item()

    async def seek(self, offset):
        # Update state immediately to reflect the seek position before DLNA device responds
        self.state.update(position=str(timedelta(milliseconds=offset)))
        await self.dlna.Seek(str(timedelta(milliseconds=offset)))
        # Force a state check on next loop to sync with actual DLNA device position
        self.state.check_all_next_loop = True

    async def get_elapsed(self):
        position_info = await self.dlna.GetPositionInfo()
        if position_info is None:
            return 0
        t = position_info.RelTime
        t = parse_timedelta(t)
        return int(t.total_seconds() * 1000)

    async def get_volume(self):
        volume = await self.dlna.GetVolume()
        volume = int(volume.CurrentVolume)
        return convert_volume(volume, self.dlna.volume_max, self.dlna.volume_min, 100, 0, 1)

    async def set_volume(self, volume):
        volume = convert_volume(volume, 100, 0, self.dlna.volume_max, self.dlna.volume_min, self.dlna.volume_step)
        await self.dlna.SetVolume(volume)
        self.state.check_all_next_loop = True

    async def is_muted(self):
        mute = await self.dlna.GetMute()
        return mute.CurrentMute

    def start_plex_tv_notify(self):
        asyncio.create_task(self._update_plex_tv_connection_loop())

    async def _update_plex_tv_connection_loop(self):
        while True:
            try:
                await self.update_plex_tv_connection()
            except Exception:
                pass
            await asyncio.sleep(60)

    async def update_plex_tv_connection(self):
        if not settings.host_ip:
            return
        if not self.plex_bind_token:
            self.plex_bind_token = settings.get_token_for_uuid(self.dlna.uuid)
            if not self.plex_bind_token:
                return
        await g.http.put(f"https://plex.tv/devices/{self.dlna.uuid}?X-Plex-Token={self.plex_bind_token}",
                         data={"Connection[][uri]": f"http://{settings.host_ip}:{settings.http_port}"},
                         headers=pms_header(self.dlna))

    def update_state(self, info):
        if info.propertyset:
            info = info.propertyset.property.LastChange.Event.InstanceID
        else:
            return
        state = info.TransportState['@val']
        uri = info.AVTransportURI['@val']
        pos = info.RelativeTimePosition['@val']
        if not state and not uri and not pos:
            print("ignoring notice no info")
            return
        if not state:
            state = ""
        if not uri:
            uri = ""
        if not pos:
            pos = ""
        if __debug__:
            print(f"{self.dlna.name} update state from sub {state} {uri} {pos}")
        self.state.update(state=state, uri=uri, position=pos)

    @property
    def plex_state(self):
        if self.state.state is None:
            return None
        if self.state.state == "PLAYING":
            return "playing"
        if self.state.state == "STOPPED":
            return "stopped"
        if self.state.state == "NO_MEDIA_PRESENT":
            return "stopped"
        if self.state.state == "PAUSED_PLAYBACK":
            return "paused"
        if self.state.state == "TRANSITIONING":
            return "playing"

    async def get_pms_state(self):
        if self.state is None:
            return None
        d = await self.get_state()
        keys = ['state', 'ratingKey', 'key', 'time', 'duration', 'playQueueItemID', 'shuffle', 'repeat', 'containerKey']
        not_wanted_keys = []
        for k, _ in d.items():
            if k not in keys:
                not_wanted_keys.append(k)
        for k in not_wanted_keys:
            del d[k]
        d['X-Plex-Token'] = self.plex_lib.token
        return d

    async def get_state(self):
        if self.state == "STOPPED" or self.state is None or self.queue is None:
            return {}
        lib_info = self.plex_lib.get_info()
        shuffle = self.shuffle
        if shuffle > 0 and not await self.queue.allow_shuffle():
            shuffle = 0
        track_info = await self.queue.get_track_info()
        time = self.state.elapsed
        volume = self.state.volume
        mute = "1" if self.state.muted else "0"
        state = {
            'state': self.plex_state,
            'time': time,
            'volume': volume,
            'mute': mute,
            'shuffle': shuffle,
            'repeat': self.queue.repeat
        }
        state.update(track_info)
        state.update(lib_info)
        if self._transport_state_override:
            state['state'] = 'paused' if self._active_operation_target_paused else 'playing'
            state['time'] = 0
        return state

    def __del__(self):
        self.state._thread_should_stop = True
        del self.state
