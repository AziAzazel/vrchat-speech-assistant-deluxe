"""Isolate configuration and platform substitutes for headless tests."""
import importlib
import os
import sys
import tempfile
import types
from unittest.mock import Mock
import pytest


def pytest_configure(config):
    # Set before test collection imports the package and initializes logging.
    config.deluxe_appdata = tempfile.TemporaryDirectory(prefix="deluxe-tests-")
    config.deluxe_previous_appdata = os.environ.get("APPDATA")
    os.environ["APPDATA"] = config.deluxe_appdata.name


def pytest_unconfigure(config):
    previous = config.deluxe_previous_appdata
    if previous is None:
        os.environ.pop("APPDATA", None)
    else:
        os.environ["APPDATA"] = previous
    # Windows cannot remove diagnostic files while their handles are open.
    import faulthandler
    import logging
    faulthandler.disable()
    diagnostics = sys.modules.get("vrchat_speech_assistant.diagnostics")
    if diagnostics and diagnostics._fatal_file:
        diagnostics._fatal_file.close()
    for handler in list(logging.getLogger("deluxe").handlers):
        handler.close()
        logging.getLogger("deluxe").removeHandler(handler)
    config.deluxe_appdata.cleanup()


@pytest.fixture(scope="session")
def gui(tmp_path_factory):
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # These platform dependencies are intentionally substituted on Linux.
    sys.modules["winsound"] = types.SimpleNamespace(PlaySound=Mock(), SND_ASYNC=1)
    sys.modules["pyaudio_devices"] = types.ModuleType("pyaudio_devices")
    sys.modules["pyaudio_devices"].get_devices = lambda **kwargs: [{"name": "Test device", "index": 0}]
    sys.modules["pyaudio_devices.devices"] = types.SimpleNamespace(
        get_devices=lambda **kwargs: [{"name": "Test device", "index": 0}])
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    main = importlib.import_module("vrchat_speech_assistant.main")
    main.get_device_snapshot = lambda: {"inputs": [{"name": "Test device", "index": 0}], "outputs": [{"name": "Test device", "index": 0}]}
    return app, main
