# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 plexdlnaplayer-enhanced contributors
#
# This file is part of plexdlnaplayer-enhanced, a fork of plexdlnaplayer.
# Original project: https://github.com/songchenwen/plexdlnaplayer

"""Virtual DLNA device management."""

from .devices import (
    load_virtual_devices,
    list_virtual_devices,
    list_virtual_devices_with_summaries,
    get_virtual_device_by_uuid,
    create_virtual_device,
    update_virtual_device,
    delete_virtual_device,
    list_physical_device_snapshots,
    VirtualDeviceError,
    CapabilityMismatchError,
    UnknownMemberError,
)

__all__ = [
    "load_virtual_devices",
    "list_virtual_devices",
    "list_virtual_devices_with_summaries",
    "get_virtual_device_by_uuid",
    "create_virtual_device",
    "update_virtual_device",
    "delete_virtual_device",
    "list_physical_device_snapshots",
    "VirtualDeviceError",
    "CapabilityMismatchError",
    "UnknownMemberError",
]
