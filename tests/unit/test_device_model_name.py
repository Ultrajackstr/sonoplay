"""device_model_name prefers UPnP modelName over modelDescription / fallback.

Regression: the AMBEO omits modelDescription, so the old code showed the
fallback product name ("SonoPlay") as the model.
"""
from dlna.dlna_device import device_model_name


def test_prefers_model_name():
    info = {"modelName": "AMBEO Soundbar", "modelDescription": "A soundbar"}
    assert device_model_name(info, "SonoPlay") == "AMBEO Soundbar"


def test_falls_back_to_description_then_product():
    assert device_model_name({"modelDescription": "Fancy Renderer"}, "SonoPlay") == "Fancy Renderer"
    assert device_model_name({}, "SonoPlay") == "SonoPlay"


def test_empty_model_name_skips_to_fallback():
    assert device_model_name({"modelName": ""}, "SonoPlay") == "SonoPlay"
