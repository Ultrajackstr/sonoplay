"""Tests for gapless next-track selection (PlexDlnaAdapter._compute_gapless_next).

Gapless pre-arms the next track via SetNextAVTransportURI so the renderer
crosses over at the true end of the current track. _compute_gapless_next is the
deterministic part: given the queue position + repeat/shuffle, which track (if
any) should we arm. It's a plain method on self, so we exercise it unbound with
a lightweight fake queue (the SetNextAVTransportURI I/O and the renderer's
auto-advance are integration behaviour, verified on the device).
"""

import asyncio
import time
import types
from unittest.mock import patch

from plex.adapters import PlexDlnaAdapter
from transport_readiness import renderer_ready_to_play


class _FakeQueue:
    def __init__(self, current, total, repeat=0):
        self._current = current
        self._total = total
        self.repeat = repeat

    async def selected_offset(self):
        return self._current

    async def total_count(self):
        return self._total

    async def track(self, offset):
        return types.SimpleNamespace(offset=offset)

    def is_track_playable(self, track):
        return True

    def url_for_track(self, track, force_transcode=False):
        return f"http://stream/{track.offset}"


def _adapter(queue, shuffle=0):
    return types.SimpleNamespace(
        queue=queue, shuffle=shuffle,
        dlna=types.SimpleNamespace(name="Ambeo"),
    )


def _next(adapter):
    return asyncio.run(PlexDlnaAdapter._compute_gapless_next(adapter))


def test_arms_next_track_in_linear_queue():
    assert _next(_adapter(_FakeQueue(current=2, total=10))) == (3, "http://stream/3")


def test_no_arm_on_last_track_without_repeat():
    assert _next(_adapter(_FakeQueue(current=9, total=10, repeat=0))) is None


def test_repeat_all_wraps_to_start():
    assert _next(_adapter(_FakeQueue(current=9, total=10, repeat=2))) == (0, "http://stream/0")


def test_repeat_one_arms_same_track():
    assert _next(_adapter(_FakeQueue(current=4, total=10, repeat=1))) == (4, "http://stream/4")


def test_shuffle_does_not_prearm():
    assert _next(_adapter(_FakeQueue(current=2, total=10), shuffle=1)) is None


def test_no_queue_returns_none():
    assert _next(_adapter(None)) is None


# --- auto-next "settling" guard after a gapless cross-over --------------------

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
    if asyncio.iscoroutine(coro):
        coro.close()
    return None


def _playing_adapter(duration, last_gapless_advance):
    return types.SimpleNamespace(
        _controlled_by_virtual_device=False,
        _suppress_auto_next=False,
        _auto_next_in_flight=False,
        _active_operation_id=0,
        queue=object(),
        shuffle=0,
        no_notice=False,
        _last_gapless_advance=last_gapless_advance,
        _gapless_settle_seconds=5.0,
        current_track_info=types.SimpleNamespace(duration=duration),
        state=types.SimpleNamespace(
            current_uri="http://stream", state="PLAYING",
            elapsed=196000, update=lambda **k: None,
        ),
        loop=object(),
        _with_no_notice=lambda coro: (
            coro.close() if asyncio.iscoroutine(coro) else None
        ) or _noop(),
    )


def test_auto_next_suppressed_during_gapless_settle():
    """A stale end-of-track position right after a gapless cross-over must not
    trigger auto-next (the freshly-started track would be skipped)."""
    adapter = _playing_adapter(duration=196920, last_gapless_advance=time.monotonic())
    changed = _Attr(elapsed=196000, old=_Attr(elapsed=195000))
    with patch("asyncio.run_coroutine_threadsafe", _consume):
        assert PlexDlnaAdapter.check_auto_next(adapter, changed) is False


def test_auto_next_fires_after_gapless_settle_window():
    """Outside the settling window, genuine end-of-track auto-next still fires."""
    adapter = _playing_adapter(duration=196920, last_gapless_advance=time.monotonic() - 100)
    changed = _Attr(elapsed=196000, old=_Attr(elapsed=195000))
    with patch("asyncio.run_coroutine_threadsafe", _consume):
        assert PlexDlnaAdapter.check_auto_next(adapter, changed) is True


# --- gapless settle-window position smoothing ---------------------------------
# The renderer briefly reports the *previous* track's near-end RelTime for a poll
# or two right after a gapless cross-over (observed on the AMBEO: 388000ms on a
# 395500ms track). The freshly-advanced track restarted at 0, so any large value
# inside the settle window is stale and must not be forwarded to the timeline.

def _smooth_adapter(last_advance, settle=5.0, slack_ms=3000):
    return types.SimpleNamespace(
        _last_gapless_advance=last_advance,
        _gapless_settle_seconds=settle,
        _gapless_settle_slack_ms=slack_ms,
    )


def _smooth(adapter, device_elapsed_ms, now):
    return PlexDlnaAdapter._settle_smoothed_time(adapter, device_elapsed_ms, now)


def test_stale_spike_during_settle_is_clamped():
    # cross-over at t=1000.0; 2s later the device emits the previous track's
    # near-end position -> clamp to wall-clock(2s)+slack(3s) = 5000ms.
    adapter = _smooth_adapter(last_advance=1000.0)
    assert _smooth(adapter, 388000, now=1002.0) == 5000


def test_plausible_position_during_settle_passes():
    # A value consistent with a freshly-started track is left untouched.
    adapter = _smooth_adapter(last_advance=1000.0)
    assert _smooth(adapter, 1500, now=1002.0) == 1500


def test_spike_outside_settle_window_passes():
    # Once the window has closed the device value is authoritative again.
    adapter = _smooth_adapter(last_advance=1000.0)
    assert _smooth(adapter, 388000, now=1010.0) == 388000


def test_no_gapless_advance_passes_through():
    # No recent cross-over -> never smooth (e.g. normal playback / explicit seek).
    adapter = _smooth_adapter(last_advance=0.0)
    assert _smooth(adapter, 388000, now=1002.0) == 388000


def test_settle_window_boundary_is_exclusive():
    # Exactly at the window edge the device value is reported as-is.
    adapter = _smooth_adapter(last_advance=1000.0)
    assert _smooth(adapter, 388000, now=1005.0) == 388000


# --- transport-operation override: don't freeze the timeline at 0 -------------
# During an explicit load (auto-next / track change) the AMBEO keeps playing the
# new track while wait_for_can_play burns its full 5s timeout. _transport_state_
# override otherwise pins time=0 for that whole window, so the new track shows
# frozen at 0:00 then jumps to 0:05. Once the renderer is on the target URI we
# report its real position instead.

def _override_adapter(target_uri, current_uri, paused=False):
    return types.SimpleNamespace(
        _active_operation_target_paused=paused,
        _active_target_uri=target_uri,
        state=types.SimpleNamespace(current_uri=current_uri),
    )


def _override_time(adapter, capped_time_ms):
    return PlexDlnaAdapter._override_reported_time(adapter, capped_time_ms)


def test_override_reports_real_time_once_on_target_uri():
    # Device has switched to the track we're loading -> report its real position.
    adapter = _override_adapter(target_uri="u://next", current_uri="u://next")
    assert _override_time(adapter, 3000) == 3000


def test_override_pins_zero_while_still_transitioning():
    # Device not yet on the target URI -> genuinely transitioning, pin 0.
    adapter = _override_adapter(target_uri="u://next", current_uri="u://old")
    assert _override_time(adapter, 3000) == 0


def test_override_pins_zero_for_pause_operation():
    # A pause load keeps the existing behaviour (0) regardless of URI.
    adapter = _override_adapter(target_uri="u://next", current_uri="u://next", paused=True)
    assert _override_time(adapter, 3000) == 0


# --- wait_for_can_play readiness predicate ------------------------------------
# The AMBEO auto-plays the reloaded URI, so GetCurrentTransportActions never
# lists "Play" and wait_for_can_play burns its full 5s timeout. _ready_to_play
# lets it return as soon as the device is confirmably playing the URI we just
# loaded (issuing Play is then a no-op -> no UPnP 701), while still waiting
# through the post-SetAVTransportURI transition / a stale previous-URI reading.

def _ready(actions="", state="", track_uri="", expected_uri=None):
    return renderer_ready_to_play(actions, state, track_uri, expected_uri)


def test_ready_when_play_in_actions():
    # Original behaviour: an idle/ready device that advertises Play.
    assert _ready(actions="Play,Stop") is True


def test_ready_when_already_playing_target_uri():
    assert _ready(state="PLAYING", track_uri="u://new", expected_uri="u://new") is True


def test_ready_when_paused_on_target_uri():
    assert _ready(state="PAUSED_PLAYBACK", track_uri="u://new", expected_uri="u://new") is True


def test_not_ready_while_transitioning_to_target():
    # Still transitioning after SetAVTransportURI -> wait (preserves 701 guard).
    assert _ready(state="TRANSITIONING", track_uri="u://new", expected_uri="u://new") is False


def test_not_ready_when_still_playing_old_uri():
    # Device still reports the previous track -> not on our new URI yet.
    assert _ready(state="PLAYING", track_uri="u://old", expected_uri="u://new") is False


def test_not_ready_playing_without_expected_uri():
    # No target supplied -> only the Play-in-actions path can signal readiness.
    assert _ready(state="PLAYING", track_uri="u://new", expected_uri=None) is False


def test_not_ready_when_idle_actions_only():
    assert _ready(actions="Stop", state="STOPPED", track_uri="", expected_uri="u://new") is False
