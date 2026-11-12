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
    from vrchat_speech_assistant.languages import GOOGLE, DEEPL, VOICES
    from vrchat_speech_assistant.providers import polly_engine, validate_polly_style, UnsupportedSpeechStyle
    assert len(GOOGLE) == 86 and len(DEEPL) == 111
    assert "Ola [Neural]" in VOICES["polly"]["Polish"]
    assert polly_engine("Matthew") == "standard"
    assert polly_engine("Ola [Neural]") == "neural"
    validate_polly_style("Ola [Neural]", {"rate": 85})
    try:
        validate_polly_style("Ola [Neural]", {"whispered": True})
    except UnsupportedSpeechStyle:
        pass
    else:
        raise AssertionError("Neural whisper was not rejected")
    for filename in ("banner.png", "logo.png", "on.wav", "off.wav"):
        assert (RESOURCES_PATH / filename).is_file(), filename
    from vrchat_speech_assistant.audio_devices import get_device_snapshot
    import pyaudio
    # Hold a parent PortAudio context while the packaged helper scans devices.
    # The helper must have a separate PID and cannot terminate this context.
    parent_audio = pyaudio.PyAudio()
    try:
        for _ in range(2):
            snapshot = get_device_snapshot()
            assert snapshot["pid"] != os.getpid()
            assert parent_audio.get_device_count() >= 0
    finally:
        parent_audio.terminate()
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
    from vrchat_speech_assistant.media_playback import MediaSpeech
    media_wav = Path(os.environ["APPDATA"]) / "media.wav"
    with wave.open(str(media_wav), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(22050)
        audio.writeframes(b"\0\0" * 5512)
    subtitles = media_wav.with_suffix(".srt")
    subtitles.write_text("1\n00:00:00,000 --> 00:00:10,000\nTest ポイ\n", encoding="utf-8")
    class CaptionProbe:
        def __init__(self):
            self.messages = []
        def send_message(self, address, arguments):
            self.messages.append((address, arguments))
    previous_driver = os.environ.get("SDL_AUDIODRIVER")
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    try:
        for recording in (media_wav, RESOURCES_PATH / "playback-smoke.mp3"):
            probe = CaptionProbe()
            with output_scope(threading.Event()):
                MediaSpeech(recording, str(subtitles), client=probe).speech("", "", None)
            assert any(args[0] == "Test ポイ" for _, args in probe.messages), "No timed subtitle"
            assert probe.messages[-1][1][0] == "", "Subtitle was not cleared"
    finally:
        if previous_driver is None:
            os.environ.pop("SDL_AUDIODRIVER", None)
        else:
            os.environ["SDL_AUDIODRIVER"] = previous_driver
    from vrchat_speech_assistant.hotkeys import GlobalHotkeys
    delivered = threading.Event()
    errors = []
    manager = GlobalHotkeys({"probe": "Ctrl+Alt+Shift+F24", "semicolon": "Ctrl+;"}, lambda action: delivered.set(), errors.append)
    manager.start()
    try:
        assert manager.ready_event.wait(5), "Native hotkey thread did not initialize"
        assert manager.registered_count == 2, errors
        assert ctypes.windll.user32.PostThreadMessageW(manager.thread_id, 0x0312, 1, 0)
        assert delivered.wait(5), "Background WM_HOTKEY was not dispatched"
        delivered.clear()
        assert ctypes.windll.user32.PostThreadMessageW(manager.thread_id, 0x0312, 2, 0)
        assert delivered.wait(5), "Semicolon WM_HOTKEY was not dispatched"
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
    from vrchat_speech_assistant.history_dialog import HistoryDialog
    from vrchat_speech_assistant.text_tools import add_random_ending, correct_nicknames
    window.ending_text.setText(", poi")
    window.ending_frequency.setValue(100)
    assert window.config["ENDING"]["frequency"] == "100"
    assert add_random_ending("Hello.", ", poi", 100) == "Hello, poi."
    assert correct_nicknames("Hello Nekosan.", {"Nekosan": "Neko-san"}) == "Hello Neko-san."
    window.cards_by_key["endings"].set_collapsed(False)
    window.cards_by_key["endings"].set_collapsed(True)
    assert window.config["UI"].getboolean("collapsed_endings")
    window.cards_by_key["endings"].set_collapsed(False)
    assert not window.config["UI"].getboolean("collapsed_endings")
    window._record_history({"id": 1, "time": "00:00:00", "status": "completed", "language": "English",
                            "source": "Hello", "result": "Hello, poi.", "spoken": "Hello, poi.",
                            "provider": "Windows Speech", "voice": "Local"})
    history = HistoryDialog(window)
    assert history.table.rowCount() == 1
    assert history.selected()["result"] == "Hello, poi."
    history.close()
    from vrchat_speech_assistant.soundboard_dialog import SoundboardDialog
    soundboard = SoundboardDialog(window)
    soundboard.show()
    app.processEvents()
    assert window.global_hotkeys is None and window._hotkey_edit_depth == 1
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    editor = soundboard.table.cellWidget(0, 0)
    editor.setFocus()
    QTest.keyClick(editor, Qt.Key_Semicolon, Qt.ControlModifier)
    assert editor.keySequence().toString() == "Ctrl+;"
    assert soundboard.table.cellWidget(0, 0).keySequence().toString() == "Ctrl+;"
    assert soundboard.table.cellWidget(0, 2).currentText() == "Japanese"
    assert soundboard.table.cellWidget(0, 5).currentText() == "Mizuki"
    soundboard.save()
    assert window._hotkey_edit_depth == 0 and window.global_hotkeys is not None
    assert window.global_hotkeys.ready_event.wait(5)
    assert window.soundboard_presets[0]["text"] == "ぽい"
    assert window.soundboard_presets[0]["output"] == "Voice only"
    window.clear_history()
    assert not window.history
    window.close()
    app.processEvents()
    Path(report).write_text(json.dumps({"version": __version__, "gui": "passed", "sapi_wav": "passed", "resources": "passed", "sapi_async_wav": "passed", "preview": "passed", "language_switch": "passed", "native_hotkeys": "passed", "responsive_ui": "passed", "pitch_saved": "passed", "history": "passed", "category_collapse": "passed", "ending_controls": "passed", "pronunciation": "passed", "upstream_catalogue": "passed", "polly_style_guard": "passed", "isolated_audio_probe": "passed", "soundboard": "passed", "semicolon_hotkey": "passed", "shortcut_recording": "passed", "wav_mp3_srt": "passed"}), encoding="utf-8")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--audio-device-probe":
        try:
            from vrchat_speech_assistant.audio_devices import write_device_probe
            write_device_probe(sys.argv[2])
            return 0
        except Exception:
            # Windowed PyInstaller must not show an unhandled-error dialog.
            return 2
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
