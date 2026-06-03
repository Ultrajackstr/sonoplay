"""Regression guard for the web UI playback buttons.

The device cards in both templates expose previous / pause / next buttons that
call a local ``sendCommand(uuid, command)``. Those must hit routes the live
FastAPI app (``plex/plexserver.py``) actually registers.

Before this guard existed both templates were calling endpoints that did not
exist on the live server, so every button 404'd ("Failed to send command"):

  * ``virtual_devices.html``    -> GET  /api/player/playback/{previous,pause,next}
  * ``discovered_devices.html`` -> POST /api/devices/${uuid}/command

The live app only exposes ``/player/playback/<canonical-name>`` (no /api prefix,
canonical names ``skipPrevious`` / ``pause`` / ``skipNext``). This test pins that
contract so the front-end URLs and the route names can't silently drift apart.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLEXSERVER = ROOT / "plex" / "plexserver.py"
TEMPLATES = {
    "discovered": ROOT / "templates" / "discovered_devices.html",
    "virtual": ROOT / "templates" / "virtual_devices.html",
}


def _registered_playback_routes():
    """Set of /player/playback/<name> paths the FastAPI app declares."""
    src = PLEXSERVER.read_text(encoding="utf-8")
    return set(re.findall(r'@s\.\w+\("(/player/playback/[^"?]+)"', src))


def _sendcommand_body(template_path):
    """Return the JS source of the sendCommand(...) function via brace matching."""
    text = template_path.read_text(encoding="utf-8")
    start = text.index("function sendCommand")
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
    raise AssertionError(f"could not find end of sendCommand in {template_path}")


def test_backend_exposes_canonical_playback_routes():
    routes = _registered_playback_routes()
    for name in ("pause", "skipNext", "skipPrevious"):
        assert f"/player/playback/{name}" in routes, (
            f"expected backend route /player/playback/{name}; got {sorted(routes)}"
        )


def test_templates_do_not_call_phantom_endpoints():
    for label, path in TEMPLATES.items():
        text = path.read_text(encoding="utf-8")
        assert "/api/player/playback/" not in text, f"{label}: stale /api/player/playback/ prefix"
        assert "/api/devices/${uuid}/command" not in text, f"{label}: phantom POST command route"


def test_templates_call_registered_playback_routes():
    routes = _registered_playback_routes()
    for label, path in TEMPLATES.items():
        body = _sendcommand_body(path)
        assert "/player/playback/" in body, f"{label}: sendCommand must fetch /player/playback/"
        assert "/api/" not in body, f"{label}: sendCommand must not call an /api/ path"
        endpoints = set(re.findall(r"""['"](skip\w+|pause|play|stop|seekTo)['"]""", body))
        assert endpoints, f"{label}: no canonical endpoint names found in sendCommand"
        for ep in endpoints:
            assert f"/player/playback/{ep}" in routes, (
                f"{label}: sendCommand maps to /player/playback/{ep} which is not a registered route"
            )


def test_templates_wire_both_play_and_pause():
    """The main transport button must offer BOTH pause (while playing) and play
    (to resume while paused). Without a wired 'play' command a paused device
    cannot be resumed from the UI -- the original bug report."""
    for label, path in TEMPLATES.items():
        text = path.read_text(encoding="utf-8")
        assert ", 'pause')" in text, f"{label}: no pause command wired"
        assert ", 'play')" in text, (
            f"{label}: no play command wired -- a paused device can't be resumed from the UI"
        )
