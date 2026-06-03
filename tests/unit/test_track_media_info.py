"""track_media_info extracts audio-quality fields from a Plex track's Media[0]."""
import types

from plex.play_queue import track_media_info


def _track(**media):
    return types.SimpleNamespace(Media=[types.SimpleNamespace(**media)])


def test_extracts_quality_fields():
    info = track_media_info(_track(
        container="flac", audioCodec="flac", bitrate=1411, audioSampleRate=44100, audioChannels=2
    ))
    assert info == {
        "container": "flac", "codec": "flac",
        "bitrate_kbps": 1411, "sample_rate_hz": 44100, "channels": 2,
    }


def test_no_media_returns_empty():
    assert track_media_info(types.SimpleNamespace()) == {}
    assert track_media_info(types.SimpleNamespace(Media=[])) == {}


def test_missing_fields_are_none():
    info = track_media_info(_track(bitrate=320))
    assert info == {
        "container": None, "codec": None,
        "bitrate_kbps": 320, "sample_rate_hz": None, "channels": None,
    }
