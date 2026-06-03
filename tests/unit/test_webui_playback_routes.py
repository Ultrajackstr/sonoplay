"""Regression guard for the web UI playback buttons.

The device cards in both templates expose previous / pause / play / next buttons
whose onclick calls a local ``sendCommand(uuid, command)``. That delegates to
``sendPlaybackCommand()`` in ``static/js/shared.js``, which builds the actual
``/player/playback/<name>`` URL. This pins:

  * the button tokens stay wired in the templates,
  * both pages delegate to the shared helper (the dedup), and
  * the shared helper only targets routes the live FastAPI app
    (``plex/plexserver.py``) actually registers,

so the front-end URLs and the route names can't silently drift apart. (Before
this guard, the templates called endpoints that didn't exist and every button
404'd "Failed to send command".)
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLEXSERVER = ROOT / "plex" / "plexserver.py"
SHARED_JS = ROOT / "static" / "js" / "shared.js"
TEMPLATES = {
    "discovered": ROOT / "templates" / "discovered_devices.html",
    "virtual": ROOT / "templates" / "virtual_devices.html",
}


def _registered_playback_routes():
    """Set of /player/playback/<name> paths the FastAPI app declares."""
    src = PLEXSERVER.read_text(encoding="utf-8")
    return set(re.findall(r'@s\.\w+\("(/player/playback/[^"?]+)"', src))


def _all_registered_routes():
    """Every path the FastAPI app declares (any HTTP verb)."""
    src = PLEXSERVER.read_text(encoding="utf-8")
    return set(re.findall(r'@s\.\w+\("([^"?]+)"', src))


def _shared_function_body(name):
    """Return the JS source of a top-level function in shared.js via brace matching."""
    text = SHARED_JS.read_text(encoding="utf-8")
    start = text.index(f"function {name}")
    depth = 0
    i = text.index("{", start)
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    raise AssertionError(f"could not find end of {name} in shared.js")


def test_backend_exposes_canonical_playback_routes():
    routes = _registered_playback_routes()
    for name in ("play", "pause", "skipNext", "skipPrevious"):
        assert f"/player/playback/{name}" in routes, (
            f"expected backend route /player/playback/{name}; got {sorted(routes)}"
        )


def test_no_phantom_playback_endpoints_anywhere():
    """The pre-fix broken endpoints must not reappear in templates or shared.js."""
    for path in [SHARED_JS, *TEMPLATES.values()]:
        text = path.read_text(encoding="utf-8")
        assert "/api/player/playback/" not in text, f"{path.name}: stale /api/player/playback/ prefix"
        assert "/api/devices/${uuid}/command" not in text, f"{path.name}: phantom POST command route"


def test_shared_sendcommand_targets_registered_routes():
    routes = _registered_playback_routes()
    body = _shared_function_body("sendPlaybackCommand")
    assert "/player/playback/" in body, "sendPlaybackCommand must fetch /player/playback/"
    assert "/api/" not in body, "sendPlaybackCommand must not call an /api/ path"
    endpoints = set(re.findall(r"""['"](skip\w+|pause|play|stop|seekTo)['"]""", body))
    assert endpoints, "no canonical endpoint names found in sendPlaybackCommand"
    for ep in endpoints:
        assert f"/player/playback/{ep}" in routes, (
            f"sendPlaybackCommand maps to /player/playback/{ep} which is not a registered route"
        )


def test_templates_delegate_sendcommand_to_shared_helper():
    """Both pages delegate to the shared helper rather than re-implement the
    fetch (the dedup); guards against a copy drifting back in."""
    for label, path in TEMPLATES.items():
        text = path.read_text(encoding="utf-8")
        assert "sendPlaybackCommand(" in text, f"{label}: sendCommand should call sendPlaybackCommand()"


def test_templates_wire_both_play_and_pause():
    """The main transport button must offer BOTH pause (while playing) and play
    (to resume while paused)."""
    for label, path in TEMPLATES.items():
        text = path.read_text(encoding="utf-8")
        assert ", 'pause')" in text, f"{label}: no pause command wired"
        assert ", 'play')" in text, (
            f"{label}: no play command wired -- a paused device can't be resumed from the UI"
        )


def test_nav_plex_widget_endpoints_exist():
    """base.html's Plex nav widget calls /api/plex-status (checkPlexStatus) and
    /api/plex-disconnect (disconnectPlex); both must be registered routes."""
    routes = _all_registered_routes()
    for path in ("/api/plex-status", "/api/plex-disconnect"):
        assert path in routes, f"{path} is called by base.html but not registered in plexserver.py"
