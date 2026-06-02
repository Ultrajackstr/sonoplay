# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure helper for deciding when a DLNA renderer can accept a Play command.

Kept dependency-free (no DLNA/HTTP imports) so it can be unit-tested directly
regardless of test import order, and imported by ``dlna.dlna_device`` without
adding to its import graph.
"""


def renderer_ready_to_play(actions, transport_state, track_uri, expected_uri):
    """True if the renderer can accept Play / is already playing the target.

    ``actions`` is GetCurrentTransportActions' ``Actions`` string; ``transport_state``
    and ``track_uri`` come from GetTransportInfo / GetPositionInfo.

    Ready when:
      * Play is advertised (an idle/stopped device — the original signal), OR
      * the device is already PLAYING/PAUSED the *exact* URI we just loaded.
        Renderers like the Rygel-based AMBEO auto-play the new URI and then never
        list "Play" (they offer Pause instead), so the action poll alone would
        always wait the full timeout. Issuing Play to a device already playing
        that URI is a harmless no-op, so there is no UPnP 701 "Transition not
        available" risk.

    NOT ready while still TRANSITIONING, or while still reporting the previous
    URI — the URI match guards against a stale reading triggering an early Play.
    """
    if actions and "Play" in actions:
        return True
    if expected_uri and track_uri == expected_uri \
            and transport_state in ("PLAYING", "PAUSED_PLAYBACK"):
        return True
    return False
