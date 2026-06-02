"""Regression tests for UPnP service-namespace version handling in xml2dict.

Background
----------
SOAP control responses from a renderer carry the service type as the XML
namespace of the ``<Action>Response`` element, e.g.::

    <u:GetPositionInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:2">

``DlnaDeviceService.control`` retrieves the payload with
``info.Envelope.Body.get(f"{action}Response")`` (dlna/dlna_device.py).  For that
lookup to succeed, ``xml2dict`` must collapse the service namespace so the key
is the bare local name ``GetPositionInfoResponse``.

The original namespace map only collapsed the ``:1`` service URIs, so any device
advertising ``AVTransport:2``/``:3`` (e.g. Rygel-based renderers such as the
Sennheiser AMBEO soundbar) left the response under a version-qualified key.
``Body.get("GetPositionInfoResponse")`` then returned ``None``, ``check()``
never updated ``elapsed``, and the Plex timeline reported ``time="0"`` for the
whole track even though audio played fine.
"""

import importlib
import sys

import pytest


def _load_real_utils():
    """Return a clean, real ``utils`` module.

    Sibling test modules in this suite replace shared modules (``utils``,
    ``xmltodict``, ``dotmap``) with ``"<stub ...>"`` MagicMock modules — and, if
    the real ones happen to be imported first, monkeypatch their attributes in
    place — without ever restoring them. Drop any such stubs and reload the real
    modules so ``xml2dict``/``parse_timedelta`` behave correctly regardless of
    test collection or execution order. Other test modules captured their own
    references at import time, so this does not disturb them.
    """
    for _name in ("utils", "xmltodict", "dotmap"):
        _mod = sys.modules.get(_name)
        if _mod is not None and getattr(_mod, "__file__", None) and "<stub" in str(_mod.__file__):
            del sys.modules[_name]
    import dotmap
    import xmltodict
    importlib.reload(dotmap)       # undo any in-place dotmap.DotMap monkeypatch
    importlib.reload(xmltodict)
    import utils
    return importlib.reload(utils)  # rebinds the real DotMap and real helpers


@pytest.fixture(autouse=True)
def _real_utils():
    """Guarantee real modules before each test, whatever ran before us."""
    _utils = _load_real_utils()
    globals()["xml2dict"] = _utils.xml2dict
    globals()["parse_timedelta"] = _utils.parse_timedelta
    yield


# Module-level bindings so the names resolve on import; the autouse fixture
# above re-binds them per test to defend against cross-test pollution.
_utils = _load_real_utils()
xml2dict = _utils.xml2dict
parse_timedelta = _utils.parse_timedelta


def _soap_response(body: str) -> str:
    return (
        '<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
        ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f"<s:Body>{body}</s:Body></s:Envelope>"
    )


def _get_position_info(version: str) -> str:
    return _soap_response(
        f'<u:GetPositionInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:{version}">'
        "<Track>1</Track>"
        "<TrackDuration>0:05:01</TrackDuration>"
        "<TrackMetaData></TrackMetaData>"
        "<TrackURI>http://192.168.60.144/track.flac</TrackURI>"
        "<RelTime>0:04:30</RelTime>"
        "<AbsTime>0:04:30</AbsTime>"
        "</u:GetPositionInfoResponse>"
    )


def test_avtransport_v2_response_is_retrievable_by_local_name():
    """The :2 response element must be reachable as 'GetPositionInfoResponse'.

    This mirrors DlnaDeviceService.control's lookup. Before the fix the key was
    namespace-qualified and this returned None.
    """
    info = xml2dict(_get_position_info("2"))
    resp = info.Envelope.Body.get("GetPositionInfoResponse")
    assert resp, "GetPositionInfoResponse not found for AVTransport:2 (namespace not collapsed)"
    assert resp.RelTime == "0:04:30"


def test_avtransport_v1_response_still_retrievable():
    """:1 devices must keep working (no regression)."""
    info = xml2dict(_get_position_info("1"))
    resp = info.Envelope.Body.get("GetPositionInfoResponse")
    assert resp
    assert resp.RelTime == "0:04:30"


def test_renderingcontrol_v2_response_is_retrievable_by_local_name():
    """RenderingControl:2 (volume/mute polling) is affected by the same bug."""
    info = xml2dict(_soap_response(
        '<u:GetVolumeResponse xmlns:u="urn:schemas-upnp-org:service:RenderingControl:2">'
        "<CurrentVolume>42</CurrentVolume>"
        "</u:GetVolumeResponse>"
    ))
    resp = info.Envelope.Body.get("GetVolumeResponse")
    assert resp, "GetVolumeResponse not found for RenderingControl:2"
    assert resp.CurrentVolume == "42"


def test_position_in_milliseconds_from_v2_response():
    """End-to-end of the broken symptom: RelTime -> elapsed milliseconds.

    This is exactly what DlnaState.check() computes for self.elapsed.
    """
    info = xml2dict(_get_position_info("2"))
    resp = info.Envelope.Body.get("GetPositionInfoResponse")
    elapsed_ms = int(parse_timedelta(resp.RelTime).total_seconds() * 1000)
    assert elapsed_ms == 270000  # 4:30, not 0


def test_lastchange_event_parsing_unaffected():
    """The shared parser must still collapse the GENA event namespace.

    Transport state arrives via NOTIFY/LastChange events; this path must be
    byte-for-byte unchanged by the service-namespace fix.
    """
    event = (
        '<e:propertyset xmlns:e="urn:schemas-upnp-org:event-1-0">'
        "<e:property><LastChange>&lt;Event/&gt;</LastChange></e:property>"
        "</e:propertyset>"
    )
    info = xml2dict(event)
    assert info.propertyset.property.LastChange == "<Event/>"
