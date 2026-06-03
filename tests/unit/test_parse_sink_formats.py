"""parse_sink_formats turns a DLNA ConnectionManager Sink string into a clean,
sorted, de-duplicated list of content types the renderer accepts."""
from dlna.dlna_device import parse_sink_formats


def test_empty_or_none():
    assert parse_sink_formats("") == []
    assert parse_sink_formats(None) == []


def test_parses_dedupes_sorts_and_strips_params():
    sink = (
        "http-get:*:audio/mpeg:DLNA.ORG_PN=MP3,"
        "http-get:*:audio/flac:*,"
        "http-get:*:audio/mpeg:*,"                       # duplicate MIME
        "http-get:*:audio/L16;rate=44100;channels=2:*,"  # params stripped
        "http-get:*:*:*"                                 # wildcard skipped
    )
    assert parse_sink_formats(sink) == ["audio/L16", "audio/flac", "audio/mpeg"]


def test_ignores_malformed_entries():
    assert parse_sink_formats("garbage,http-get:*:audio/flac:*") == ["audio/flac"]
