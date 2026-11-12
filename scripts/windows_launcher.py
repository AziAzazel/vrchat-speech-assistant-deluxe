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
            playback_errors = []
            def play_media():
                try:
                    with output_scope(threading.Event()):
                        MediaSpeech(recording, str(subtitles), client=probe).speech("", "", None)
                except Exception as error:
                    playback_errors.append(error)
            playback_thread = threading.Thread(target=play_media, daemon=True)
            playback_thread.start()
            playback_thread.join(10)
            assert not playback_thread.is_alive(), "Worker audio playback did not finish"
            if playback_errors:
                raise playback_errors[0]
            assert any(args[0] == "Test ポイ" for _, args in probe.messages), "No timed subtitle"
            assert probe.messages[-1][1][0] == "", "Subtitle was not cleared"
    finally:
        if previous_driver is None:
            os.environ.pop("SDL_AUDIODRIVER", None)
        else:
            os.environ["SDL_AUDIODRIVER"] = previous_driver
    from vrchat_speech_assistant.live_chatbox import LiveChatbox
    from vrchat_speech_assistant.output_control import playback_scope
    from vrchat_speech_assistant.providers import read_ogg_file
    caption_wav = Path(os.environ["APPDATA"]) / "caption-clock.wav"
    with wave.open(str(caption_wav), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(22050)
        audio.writeframes(b"\0\0" * 66150)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    try:
        for recording in (caption_wav, RESOURCES_PATH / "chatbox-smoke.ogg"):
            import pygame.mixer
            pages_sent = []
            def show_caption(text):
                if pages_sent:
                    assert pygame.mixer.music.get_busy(), "Next page arrived after audio ended"
                pages_sent.append(text)
            captions = LiveChatbox("Visible page test " * 16, show_caption)
            assert len(captions.pages) == 2
            captions.start()
            assert len(pages_sent) == 1  # Before audio starts.
            with output_scope(threading.Event()), playback_scope(captions.progress):
                read_ogg_file(str(recording), None)
            assert pages_sent == captions.pages
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
    def edge_progress(stage):
        Path(report).write_text(json.dumps({"version": __version__, "stage": stage}), encoding="utf-8")
    edge_progress("youtube_edge_lookup")
    from vrchat_speech_assistant.youtube_player import EdgePlayer, find_edge
    assert find_edge() is not None, "Windows runner has no Microsoft Edge"
    edge_probe = EdgePlayer(Path(os.environ["APPDATA"]) / "edge-smoke-profile")
    try:
        edge_progress("youtube_edge_launch")
        edge_probe._launch("about:blank")  # No network or actual YouTube playback in CI.
        edge_progress("youtube_edge_created")
        QTest.qWait(1200)
        edge_progress("youtube_edge_check")
        assert edge_probe.is_running, "Owned Edge browser did not remain running"
    finally:
        edge_progress("youtube_edge_stopping")
        edge_probe.stop()
    edge_progress("youtube_edge_stopped")
    assert not edge_probe.is_running
    from vrchat_speech_assistant.youtube_dialog import YouTubeDialog
    youtube_panel = YouTubeDialog(window)
    assert "Edge" in youtube_panel.windowTitle()
    assert "Speech device selector does not change Edge" in youtube_panel.routing.text()
    youtube_panel.close()
    youtube_panel.timer.stop()
    from vrchat_speech_assistant.providers import Polly, PollyPool
    # Construct the optional SDK client using fake explicit credentials: no AWS
    # request or credential discovery. Lazy import must still be packaged fully.
    polly_probe = Polly("test-access", "test-secret", "us-west-2")
    assert polly_probe.client.meta.service_model.service_name == "polly"
    polly_probe.client.close()
    from vrchat_speech_assistant.settings_store import SettingsStore
    import configparser
    probe_config = configparser.ConfigParser()
    probe_config["CHECK"] = {"value": "initial"}
    store = SettingsStore(Path(os.environ["APPDATA"]) / "settings-smoke.ini")
    with store.batch():
        store.save(probe_config)
        probe_config["CHECK"]["value"] = "final"
        store.save(probe_config)
    assert "final" in store.path.read_text(encoding="utf-8")
    assert not store.save(probe_config)
    window.clear_history()
    assert not window.history
    window.close()
    app.processEvents()
    Path(report).write_text(json.dumps({"version": __version__, "gui": "passed", "sapi_wav": "passed", "resources": "passed", "sapi_async_wav": "passed", "preview": "passed", "language_switch": "passed", "native_hotkeys": "passed", "responsive_ui": "passed", "pitch_saved": "passed", "history": "passed", "category_collapse": "passed", "ending_controls": "passed", "pronunciation": "passed", "upstream_catalogue": "passed", "polly_style_guard": "passed", "isolated_audio_probe": "passed", "soundboard": "passed", "semicolon_hotkey": "passed", "shortcut_recording": "passed", "wav_mp3_srt": "passed", "youtube_edge": "passed", "settings_store": "passed", "lazy_polly_sdk": "passed", "live_chatbox": "passed"}), encoding="utf-8")


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
        try:
            smoke_test(sys.argv[2])
            return 0
        except Exception as error:
            import traceback
            previous = {}
            report_path = Path(sys.argv[2])
            if report_path.is_file():
                previous = json.loads(report_path.read_text(encoding="utf-8"))
            frames = [{"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
                      for frame in traceback.extract_tb(error.__traceback__)]
            native_code = getattr(error, "winerror", None)
            previous.update(status="failed", exception_type=type(error).__name__, frames=frames,
                            native_code=native_code if isinstance(native_code, int) else None)
            report_path.write_text(json.dumps(previous), encoding="utf-8")
            return 1
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
