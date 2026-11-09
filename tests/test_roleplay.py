from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from vrchat_speech_assistant.hotkeys import parse_hotkey, GlobalHotkeys
from vrchat_speech_assistant.roleplay import PERSONALITIES, spoken_delivery, announcement


def test_hotkey_validation_and_normalization():
    assert parse_hotkey("Ctrl+Alt+F5") == (3, 116)
    assert parse_hotkey("Alt+Ctrl+F5") == parse_hotkey("Ctrl+Alt+F5")
    assert parse_hotkey("Ctrl+J") == (2, ord("J"))
    for bad in ("J", "Ctrl+Delete", "Ctrl+F25", "Ctrl+K, Ctrl+L", "", "Ctrl++"):
        with pytest.raises(ValueError):
            parse_hotkey(bad)


def test_personality_lines_and_stutter():
    assert announcement("Corporate AI", "greeting") != announcement("Rogue intelligence", "greeting")
    assert spoken_delivery("Hello friend", {"stutter": True}) == "Hello… Hello friend"
    assert spoken_delivery("Hello friend", {}) == "Hello friend"


def test_global_registration_routing_conflicts_and_cleanup(monkeypatch):
    from vrchat_speech_assistant import hotkeys
    api = Mock()
    api.RegisterHotKey.side_effect = [True, False]
    activated, reports = [], []
    manager = GlobalHotkeys({"greeting": "Ctrl+Alt+F5", "goodbye": "Ctrl+Alt+F6"}, activated.append, reports.append)
    emitted = False
    def peek(pointer, *args):
        nonlocal emitted
        if not emitted:
            emitted = True
            pointer._obj.wParam = 1
            return 1
        manager.stop_event.set()
        return 0
    api.PeekMessageW.side_effect = peek
    monkeypatch.setattr(hotkeys.sys, "platform", "win32")
    monkeypatch.setattr(hotkeys.ctypes, "windll", SimpleNamespace(user32=api), raising=False)
    manager._run()
    assert activated == ["greeting"]
    assert "unavailable" in reports[0]
    assert api.RegisterHotKey.call_args_list[0].args[2] & 0x4000
    api.UnregisterHotKey.assert_called_once_with(None, 1)
