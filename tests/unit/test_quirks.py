"""Device quirks registry: get_device_quirks should expose only the quirks the
live code actually consults (subscription_timeout, ignore_premature_stopped)."""
import types

import plex.adapters  # noqa: F401  (resolves the dlna<->plex import cycle)
from dlna.quirks import get_device_quirks


def _dev(uuid, manufacturer=None, model=None):
    return types.SimpleNamespace(uuid=uuid, manufacturer=manufacturer, model=model)


def test_unknown_device_gets_defaults_only():
    q = get_device_quirks(_dev("test-quirks-unknown"))
    assert q == {"ignore_premature_stopped": True, "subscription_timeout": None}


def test_denon_gets_subscription_timeout():
    # model must be a string for the model pattern (".*") to match.
    q = get_device_quirks(_dev("test-quirks-denon", manufacturer="Denon", model="AVR-X1700H"))
    assert q["subscription_timeout"] == 540
    assert q["ignore_premature_stopped"] is True


def test_no_dead_quirk_keys_present():
    # wait_for_can_play / detect_end_by_elapsed / control_timeout were defined but
    # never consulted; they must no longer appear in the resolved quirks (Sony's
    # entry previously injected wait_for_can_play).
    q = get_device_quirks(_dev("test-quirks-sony", manufacturer="Sony", model="HT-A9"))
    for dead in ("wait_for_can_play", "detect_end_by_elapsed", "control_timeout"):
        assert dead not in q
