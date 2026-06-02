import sys
from unittest.mock import MagicMock

# If a prior test stubbed 'utils' as a MagicMock, remove it so we can
# import the real package.
for _key in list(sys.modules):
    if _key == "utils" or _key.startswith("utils."):
        _mod = sys.modules[_key]
        if isinstance(_mod, MagicMock) or (
            hasattr(_mod, "__file__") and _mod.__file__ and "<stub" in str(_mod.__file__)
        ):
            del sys.modules[_key]

from utils import unescape_xml, redact_token


def test_unescape_lt_gt():
    assert unescape_xml(b"&lt;a&gt;") == "<a>"


def test_redact_token_in_query():
    url = "https://h:32400/library/parts/1/file.flac?X-Plex-Token=transient-abc123&foo=1"
    assert redact_token(url) == "https://h:32400/library/parts/1/file.flac?X-Plex-Token=***&foo=1"


def test_redact_token_as_trailing_param():
    assert redact_token("https://plex.tv/devices/x?X-Plex-Token=secretvalue") == \
        "https://plex.tv/devices/x?X-Plex-Token=***"


def test_redact_token_ampersand_param():
    assert redact_token("a=1&X-Plex-Token=tok-123&b=2") == "a=1&X-Plex-Token=***&b=2"


def test_redact_token_no_token_unchanged():
    assert redact_token("http://h/file.flac?foo=1") == "http://h/file.flac?foo=1"


def test_redact_token_non_str_is_stringified():
    assert redact_token(None) == "None"


def test_unescape_amp():
    assert "Tom & Jerry" == unescape_xml(b"Tom &amp; Jerry")


def test_unescape_apos():
    assert "it's" == unescape_xml(b"it&apos;s")


def test_unescape_quot():
    assert 'say "hi"' == unescape_xml(b'say &quot;hi&quot;')


def test_unescape_all_entities():
    raw = b"&lt;a href=&quot;x&quot;&gt;R&amp;D&apos;s&lt;/a&gt;"
    assert '<a href="x">R&D\'s</a>' == unescape_xml(raw)
