"""The DLNA SUBSCRIBE timeout must honor a device's subscription_timeout quirk.

Regression: loop_subscribe / DlnaDevice.subscribe used to hardcode
timeout_sec=120, so DlnaDeviceService.subscribe's None->quirk branch never
fired and the HEOS/Denon/Marantz quirk value was never sent to the device.
"""
import inspect
import types

import plex.adapters  # noqa: F401  (resolves the dlna<->plex import cycle)
from settings import settings
from dlna.dlna_device import DlnaDevice, resolve_subscribe_timeout


def _dev(uuid, manufacturer=None, model=None):
    return types.SimpleNamespace(uuid=uuid, manufacturer=manufacturer, model=model)


def test_explicit_timeout_wins():
    assert resolve_subscribe_timeout(_dev("explicit"), 300) == 300


def test_non_quirk_device_uses_global_default():
    # No matching quirk -> the global setting (120 by default). This is the
    # AMBEO case: behavior is unchanged.
    assert resolve_subscribe_timeout(_dev("plain")) == settings.dlna_subscribe_timeout


def test_denon_quirk_timeout_is_applied():
    # The bug: this 540 was previously unreachable because callers passed 120.
    dev = _dev("denon", manufacturer="Denon", model="AVR-X1700H")
    assert resolve_subscribe_timeout(dev) == 540


def test_subscribe_wrappers_default_to_quirk_resolution():
    # The bug was a hardcoded timeout_sec=120 default that bypassed the quirk.
    for name in ("subscribe", "loop_subscribe"):
        sig = inspect.signature(getattr(DlnaDevice, name))
        assert sig.parameters["timeout_sec"].default is None, (
            f"{name} must default timeout_sec=None so the subscription_timeout quirk is consulted"
        )
