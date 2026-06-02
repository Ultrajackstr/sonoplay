"""Tests for gapless next-track selection (PlexDlnaAdapter._compute_gapless_next).

Gapless pre-arms the next track via SetNextAVTransportURI so the renderer
crosses over at the true end of the current track. _compute_gapless_next is the
deterministic part: given the queue position + repeat/shuffle, which track (if
any) should we arm. It's a plain method on self, so we exercise it unbound with
a lightweight fake queue (the SetNextAVTransportURI I/O and the renderer's
auto-advance are integration behaviour, verified on the device).
"""

import asyncio
import types

from plex.adapters import PlexDlnaAdapter


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
