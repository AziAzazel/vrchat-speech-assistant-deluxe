"""Entry point for the standalone Windows executable and its build smoke test."""
import json
import os
from pathlib import Path
import sys
import tempfile
import wave
import threading
import ctypes

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def smoke_test(report):
    os.environ["APPDATA"] = tempfile.mkdtemp(prefix="deluxe-smoke-")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    from vrchat_speech_assistant._version import __version__
    from vrchat_speech_assistant.main import VRCSpeechAssistantWindow, RESOURCES_PATH
    from vrchat_speech_assistant.windows_speech import WindowsSpeech
    from vrchat_speech_assistant import darkstyle
    from vrchat_speech_assistant.piper_speech import PiperSpeech
    for filename in ("banner.png", "logo.png", "on.wav", "off.wav"):
        assert (RESOURCES_PATH / filename).is_file(), filename
    speech = WindowsSpeech()
    assert speech.voices, "No SAPI desktop voices on build runner"
    path = Path(os.environ["APPDATA"]) / "sapi.wav"
    speech.render("Speech assistant build verification.", next(iter(speech.voices)), path)
    with wave.open(str(path)) as audio:
        assert audio.getnframes() > 0
    from vrchat_speech_assistant.output_control import output_scope
    with output_scope(threading.Event()):
        speech.render("Asynchronous speech verification.", next(iter(speech.voices)), path, rate=85)
    with wave.open(str(path)) as audio:
        assert audio.getnframes() > 0
    from vrchat_speech_assistant.hotkeys import GlobalHotkeys
    delivered = threading.Event()
    errors = []
    manager = GlobalHotkeys({"probe": "Ctrl+Alt+Shift+F24"}, lambda action: delivered.set(), errors.append)
    manager.start()
    try:
        assert manager.ready_event.wait(5), "Native hotkey thread did not initialize"
        assert manager.registered_count == 1, errors
        assert ctypes.windll.user32.PostThreadMessageW(manager.thread_id, 0x0312, 1, 0)
        assert delivered.wait(5), "Background WM_HOTKEY was not dispatched"
    finally:
        manager.stop()
    app = QtWidgets.QApplication([])
    darkstyle.apply(app)
    window = VRCSpeechAssistantWindow()
    window.show()
    app.processEvents()
    assert window.isVisible()
    assert window.config["SPEECH"]["provider"] == "Windows Speech"
    assert window.global_shortcuts_checkbox.isChecked()
    window.resize(1350, 800)
    app.processEvents()
    assert window.responsive_cards.columns >= 2
    window.speech_pitch_slider.setValue(-15)
    assert window.config["SPEECH"]["pitch"] == "-15"
    window._submit_recognized("Packaged transcript preview")
    assert window.pending_draft and window.preview_timer.isActive()
    window.edit_message_button.click()
    assert not window.preview_timer.isActive()
    window.stop_speaking()
    window.manual_text.clear()
    window.switch_language()
    assert window.config["SPEECH"]["source_language"] == "Polish"
    window.switch_language()
    assert window.config["SPEECH"]["source_language"] == "English"
    window.close()
    app.processEvents()
    Path(report).write_text(json.dumps({"version": __version__, "gui": "passed", "sapi_wav": "passed", "resources": "passed", "sapi_async_wav": "passed", "preview": "passed", "language_switch": "passed", "native_hotkeys": "passed", "responsive_ui": "passed", "pitch_saved": "passed"}), encoding="utf-8")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        smoke_test(sys.argv[2])
        return 0
    from PySide6 import QtWidgets
    from vrchat_speech_assistant import darkstyle
    from vrchat_speech_assistant.main import VRCSpeechAssistantWindow
    app = QtWidgets.QApplication([])
    darkstyle.apply(app)
    window = VRCSpeechAssistantWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
