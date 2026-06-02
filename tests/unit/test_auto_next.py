"""Tests for end-of-track auto-next / false-stop decisions in PlexDlnaAdapter.

These heuristics were originally calibrated when the DLNA position was stuck at
0 (see the AVTransport:2 namespace bug). Now that position is accurate, two of
them over-fire:

* check_auto_next had a "predictive" branch that fired when the 1-second-
  resolution elapsed reached ``duration // 1000 * 1000`` (the last whole
  second) — up to ~1s before the true end — cutting the track short.
* _check_post_operation_false_stop treated a STOP at the natural end of a track
  (shortly after a seek) as a "false stop" and replayed it.

The decision methods only read attributes on ``self`` and schedule a coroutine,
so we exercise them as unbound methods with a lightweight stand-in ``self`` and
a patched scheduler — no full adapter construction needed.
"""

import asyncio
import time
import types
from unittest.mock import patch

from plex.adapters import PlexDlnaAdapter


class _Attr(dict):
    """Minimal DotMap stand-in: attribute access; missing key -> falsy empty."""

    def __getattr__(self, key):
        val = self.get(key)
        return val if val is not None else _Attr()

    def __bool__(self):
        return len(self) > 0


async def _noop():
    return None


def _consume(coro, *args, **kwargs):
    """Stand-in for asyncio.run_coroutine_threadsafe: close fire-and-forget
    coroutines so the test neither runs nor leaks them."""
    if asyncio.iscoroutine(coro):
        coro.close()
    return None


def _playing_adapter(duration, elapsed):
    return types.SimpleNamespace(
        _controlled_by_virtual_device=False,
        _suppress_auto_next=False,
        _auto_next_in_flight=False,
        _active_operation_id=0,
        queue=object(),
        shuffle=0,
        no_notice=False,
        current_track_info=types.SimpleNamespace(duration=duration),
        state=types.SimpleNamespace(
            current_uri="http://stream", state="PLAYING",
            elapsed=elapsed, update=lambda **k: None,
        ),
        loop=object(),
        _with_no_notice=lambda coro: (
            coro.close() if asyncio.iscoroutine(coro) else None
        ) or _noop(),
    )


def test_auto_next_does_not_fire_before_true_end():
    """elapsed at the last whole second (196000 of a 196920 ms track) must NOT
    trigger auto-next; firing there cuts ~1s of audio."""
    adapter = _playing_adapter(duration=196920, elapsed=196000)
    changed = _Attr(elapsed=196000, old=_Attr(elapsed=195000))
    with patch("asyncio.run_coroutine_threadsafe", _consume):
        fired = PlexDlnaAdapter.check_auto_next(adapter, changed)
    assert fired is False


def test_auto_next_still_fires_when_position_resets_to_zero_at_end():
    """The reliable end signal — position resets to 0 within ~2s of duration —
    must still trigger auto-next (no regression)."""
    adapter = _playing_adapter(duration=261946, elapsed=0)
    changed = _Attr(elapsed=0, old=_Attr(elapsed=260000))
    with patch("asyncio.run_coroutine_threadsafe", _consume):
        fired = PlexDlnaAdapter.check_auto_next(adapter, changed)
    assert fired is True


def _false_stop_adapter(elapsed, duration, since_finish=0.5):
    return types.SimpleNamespace(
        _in_false_stop_recovery=False,
        _last_operation_finish_time=time.monotonic() - since_finish,
        _post_operation_protection_window=2.0,
        _suppress_auto_next=False,
        queue=object(),
        loop=object(),
        dlna=types.SimpleNamespace(name="Ambeo"),
        state=types.SimpleNamespace(elapsed=elapsed, current_track_duration=duration),
        play_selected_queue_item=lambda *a, **k: _noop(),
    )


def test_false_stop_recovery_skips_natural_end_of_track():
    """A STOP at the end of a track (elapsed ~= duration), even shortly after a
    seek, is the natural end — it must NOT trigger a replay."""
    adapter = _false_stop_adapter(elapsed=223000, duration=223000)
    changed = _Attr(state="STOPPED", old=_Attr(state="PLAYING"))
    with patch("asyncio.run_coroutine_threadsafe", _consume):
        recovered = PlexDlnaAdapter._check_post_operation_false_stop(adapter, changed)
    assert recovered is False


def test_false_stop_recovery_still_fires_at_track_start():
    """A STOP right after load with very low elapsed IS a false stop and must
    still trigger recovery (no regression)."""
    adapter = _false_stop_adapter(elapsed=500, duration=200000)
    changed = _Attr(state="STOPPED", old=_Attr(state="PLAYING"))
    with patch("asyncio.run_coroutine_threadsafe", _consume):
        recovered = PlexDlnaAdapter._check_post_operation_false_stop(adapter, changed)
    assert recovered is True
