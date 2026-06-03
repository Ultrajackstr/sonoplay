"""Characterize extract_value's mapping unwrapping.

The previously-duplicated isinstance(DotMap)/isinstance(dict) branches were
merged into one dict check, which is valid precisely because DotMap subclasses
dict (asserted below). The dict cases therefore also exercise the DotMap path.

NOTE: we deliberately do NOT construct DotMap() instances here -- a sibling test
reloads the dotmap module, after which constructing the pre-reload DotMap class
raises a super() TypeError. issubclass() needs no instance and is reload-safe.
"""
from dotmap import DotMap
from utils import extract_value


def test_dotmap_subclasses_dict():
    # The invariant the branch-merge relies on.
    assert issubclass(DotMap, dict)


def test_none_returns_default():
    assert extract_value(None, "d") == "d"
    assert extract_value(None) is None


def test_scalar_passthrough():
    assert extract_value("hello") == "hello"
    assert extract_value(5) == 5


def test_at_val_key_is_unwrapped():
    assert extract_value({"@val": "42"}) == "42"


def test_single_value_mapping_is_unwrapped():
    assert extract_value({"only": "x"}) == "x"


def test_multi_value_returns_default_else_mapping():
    multi = {"a": 1, "b": 2}
    assert extract_value(multi, "d") == "d"
    assert extract_value(multi) == multi


def test_list_takes_first_else_default():
    assert extract_value(["a", "b"]) == "a"
    assert extract_value([]) is None
    assert extract_value([], "d") == "d"
