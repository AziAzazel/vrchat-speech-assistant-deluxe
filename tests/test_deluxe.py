"""Headless GUI integration; cloud services and Windows devices are simulated."""
import importlib
import sys
import time
import types
from pathlib import Path
from unittest.mock import Mock

import pytest




@pytest.fixture
def window(gui, monkeypatch):
    app, main = gui
    monkeypatch.setattr(main.VRCSpeechAssistantWindow, "_init_translator", lambda self: None)
    monkeypatch.setattr(main.VRCSpeechAssistantWindow, "_check_selected_speech_provider", lambda self: None)
    window = main.VRCSpeechAssistantWindow()
    window.preview_checkbox.setChecked(False)
    window.speech_provider = Mock()
    yield window
    wait_output(app, window)
    window.close()
    app.processEvents()


def wait_output(app, window):
    deadline = time.monotonic() + 3
    while window.output_busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    app.processEvents()
    assert not window.output_busy


def test_corrections(gui):
    from vrchat_speech_assistant.text_tools import correct_nicknames
    assert correct_nicknames("NEKO san, neko! nekosan", {"neko san": "Nekosan", "neko": "Cat"}) == "Nekosan, Cat! nekosan"
    assert correct_nicknames("Ann met Bob", {"Ann": "Bob", "Bob": "Rob"}) == "Bob met Rob"
    assert correct_nicknames("a+b?", {"a+b": "Name"}) == "Name?"


def test_manual_speech_settings_and_chatbox(gui, window, monkeypatch):
    app, main = gui
    chatbox = Mock()
    monkeypatch.setattr(main, "write_chatbox", chatbox)
    window.corrections = {"neko san": "Nekosan"}
    window.extra_tags = {"whispered": True, "pitch": -10}
    window.manual_text.setPlainText("Hello neko san & friends!")
    window.speak_button.click()
    wait_output(app, window)
    window.speech_provider.speech.assert_called_once_with(
        "Hello Nekosan & friends!", window.config["SPEECH"]["voice"], "Test device",
        {"whispered": True, "pitch": -10})
    chatbox.assert_not_called()
    window.manual_chatbox.setChecked(True)
    window.speak_button.click()
    wait_output(app, window)
    assert chatbox.call_args.args[1] == "Hello Nekosan & friends!"


def test_translation_shared_with_recognition(gui, window, monkeypatch):
    app, main = gui
    monkeypatch.setattr(main, "write_chatbox", Mock())
    window.corrections = {"neko san": "Nekosan"}
    window.config["SPEECH"]["target_language"] = "French"
    window.translator = Mock()
    window.translator.translate_text.return_value.text = "Bonjour Nekosan"
    window.recognize(Mock(recognize_google=Mock(return_value="Hello neko san")), object())
    app.processEvents()
    wait_output(app, window)
    assert window.translator.translate_text.call_args.args[0] == "Hello Nekosan"
    assert window.speech_provider.speech.call_args.args[0] == "Bonjour Nekosan"


def test_failure_logged_without_transcript(gui, window):
    app, main = gui
    window.speech_provider.speech.side_effect = RuntimeError("SECRET_TRANSCRIPT_OR_KEY")
    window.manual_text.setPlainText("PRIVATE_MESSAGE")
    window.speak_button.click()
    wait_output(app, window)
    assert window.speak_button.isEnabled()
    assert "failed" in window.log_line_edit.text()
    log = (main.DATA_DIR / "logs/application.log").read_text()
    assert "RuntimeError" in log and "Synthesis/audio playback" in log
    assert "SECRET_TRANSCRIPT_OR_KEY" not in log
    assert "PRIVATE_MESSAGE" not in log


def test_empty_and_large_input(gui, window):
    window.speak_manual_text()
    window.manual_text.setPlainText("a" * 2501)
    window.speak_manual_text()
    window.speech_provider.speech.assert_not_called()


def test_no_overlapping_outputs(gui, window):
    import threading
    app, main = gui
    release = threading.Event()
    window.speech_provider.speech.side_effect = lambda *args: release.wait(2)
    window.manual_text.setPlainText("first")
    window.speak_manual_text()
    try:
        assert not window.speak_button.isEnabled()
        window.speak_manual_text()
    finally:
        release.set()
    wait_output(app, window)
    assert window.speech_provider.speech.call_count == 1


def test_provider_escapes_ssml_and_uses_safe_cache(gui, tmp_path, monkeypatch):
    import io
    from vrchat_speech_assistant import providers
    monkeypatch.setattr(providers, "VOICES_PATH", tmp_path)
    playback = Mock()
    monkeypatch.setattr(providers, "read_ogg_file", playback)
    provider = providers.Polly.__new__(providers.Polly)
    provider.client = Mock()
    provider.client.synthesize_speech.side_effect = lambda **kwargs: {"AudioStream": io.BytesIO(b"audio")}
    text = "<hello> & friends " * 100
    provider.speech(text, "Justin", "Virtual cable", {"whispered": True, "pitch": -10})
    request = provider.client.synthesize_speech.call_args.kwargs
    assert "&lt;hello&gt; &amp; friends" in request["Text"]
    assert '<prosody pitch="-10%">' in request["Text"]
    path = Path(playback.call_args.args[0])
    assert len(path.stem) == 64 and path.read_bytes() == b"audio"
    provider.speech(text, "Justin", "Virtual cable", {"whispered": True, "pitch": -10})
    assert provider.client.synthesize_speech.call_count == 1


def test_device_zero_can_start_and_stop(gui, window, monkeypatch):
    app, main = gui
    recognizer = Mock()
    microphone = Mock()
    monkeypatch.setattr(main.speech_recognition, "Microphone", microphone)
    monkeypatch.setattr(main.speech_recognition, "Recognizer", lambda: recognizer)
    monkeypatch.setattr(main, "BackgroundListener", Mock())
    window.start_listener()
    microphone.assert_called_once_with(device_index=0)
    assert window.is_listener_running
    window.stop_listener()
    assert not window.is_listener_running


def test_local_provider_switch_and_optional_credentials(gui, window, monkeypatch):
    app, main = gui
    from vrchat_speech_assistant.windows_speech import SpeechWithFallback
    local = Mock(voices={"Local English": "id"})
    window.windows_speech = local
    window.speech_provider_combo.setCurrentText("Windows Speech")
    window._append_voices_for_selected_provider()
    # Other tests patch provider initialization; restore its real implementation here.
    monkeypatch.undo()
    cloud = Mock()
    monkeypatch.setattr(main, "Polly", cloud)
    window._check_selected_speech_provider()
    assert window.speech_provider is local
    assert window.config["SPEECH"]["voice"] == "Local English"
    assert not window.extra_tags_combo.isEnabled()
    window.polly_fallback_checkbox.setChecked(True)
    assert isinstance(window.speech_provider, SpeechWithFallback)
    cloud.assert_not_called()
    window.speech_provider_combo.setCurrentText("Amazon Polly")
    assert window.config["SPEECH"]["voice"] in main.VOICES["polly"][window.target_language_combo.currentText()]
    assert window.extra_tags_combo.isEnabled()


def test_settings_save_without_aws_or_deepl(gui, window, monkeypatch):
    app, main = gui
    from vrchat_speech_assistant import widgets
    window.config["SPEECH"]["provider"] = "Windows Speech"
    monkeypatch.setattr(widgets.utils, "test_deepl", lambda key: None)
    dialog = widgets.ConfigDialog(window)
    assert dialog._check_deepl_and_aws()
    dialog.close()


def test_chatbox_additions_do_not_change_speech(gui, window, monkeypatch):
    app, main = gui
    chatbox = Mock()
    monkeypatch.setattr(main, "write_chatbox", chatbox)
    window.chatbox_rules = {"hello": "👋", "friends": "[friendly AI]"}
    window.keyword_additions_checkbox.setChecked(True)
    window.manual_chatbox.setChecked(True)
    window.manual_text.setPlainText("Hello friends!")
    window.speak_manual_text()
    wait_output(app, window)
    assert window.speech_provider.speech.call_args.args[0] == "Hello friends!"
    assert chatbox.call_args.args[1] == "Hello friends! 👋 [friendly AI]"
    window.keyword_additions_checkbox.setChecked(False)
    window.speak_manual_text()
    wait_output(app, window)
    assert chatbox.call_args.args[1] == "Hello friends!"


def test_piper_provider_selection(gui, window, monkeypatch):
    app, main = gui
    from vrchat_speech_assistant.piper_speech import PiperSpeech
    window.config["SPEECH"]["piper_model"] = "/voices/english.onnx"
    window.speech_provider_combo.setCurrentText("Piper (offline)")
    monkeypatch.undo()
    window.config["SPEECH"]["polly_fallback"] = "False"
    window._check_selected_speech_provider()
    assert isinstance(window.speech_provider, PiperSpeech)
    assert window.speech_provider.model == "/voices/english.onnx"
    assert window.speech_voice_combo.currentText() == "english"


def test_personality_hotkey_and_chatbox_tag(gui, window, monkeypatch):
    app, main = gui
    chatbox = Mock()
    monkeypatch.setattr(main, "write_chatbox", chatbox)
    settings = window.config["ROLEPLAY"]
    settings["personality"] = "Corporate AI"
    settings["chatbox_tag"] = "True"
    settings["delivery"] = "Normal"
    window._init_hotkeys()
    greeting = next(s for s in window.shortcuts if s.key().toString() == "Ctrl+Alt+F5")
    greeting.activated.emit()
    wait_output(app, window)
    assert window.speech_provider.speech.call_args.args[0] == "Welcome. Your interaction is appreciated."
    assert chatbox.call_args.args[1].startswith("[CORPORATE AI] ")
    settings["phrase_greeting"] = "Greetings, human."
    window.roleplay_action("greeting")
    wait_output(app, window)
    assert window.speech_provider.speech.call_args.args[0] == "Greetings, human."


def test_expressive_delivery_speech_only_and_no_implicit_cloud(gui, window, monkeypatch):
    app, main = gui
    chatbox = Mock()
    monkeypatch.setattr(main, "write_chatbox", chatbox)
    settings = window.config["ROLEPLAY"]
    settings["chatbox_tag"] = "False"
    settings["delivery"] = "Malfunction"
    window.manual_text.setPlainText("Hello human")
    window.manual_chatbox.setChecked(True)
    window.speak_manual_text()
    wait_output(app, window)
    call = window.speech_provider.speech.call_args
    assert call.args[0] == "Hello… Hello human"
    assert call.args[3]["rate"] == 75
    assert chatbox.call_args.args[1] == "Hello human"
    window.speech_provider.reset_mock()
    settings["delivery"] = "Confidential whisper"
    window.config["SPEECH"]["provider"] = "Windows Speech"
    window.speak_manual_text()
    window.speech_provider.speech.assert_not_called()
    settings["delivery"] = "Normal"


def test_roleplay_settings_save_and_preserve_deepl_formality(gui, window):
    from vrchat_speech_assistant.roleplay_dialog import RoleplayDialog
    window.config["TRANSLATOR"]["formality"] = "Informal"
    dialog = RoleplayDialog(window)
    dialog.personality.setCurrentText("Rogue intelligence")
    dialog.global_keys.setChecked(False)
    dialog.table.cellWidget(0, 2).setText("Custom greeting")
    dialog.save()
    assert window.config["ROLEPLAY"]["personality"] == "Rogue intelligence"
    assert window.config["ROLEPLAY"]["delivery"] == "Measured"
    assert window.config["ROLEPLAY"]["phrase_greeting"] == "Custom greeting"
    assert window.config["TRANSLATOR"]["formality"] == "Informal"
    assert len(window.shortcuts) == 10
    window.config["ROLEPLAY"]["delivery"] = "Normal"


def test_polly_delivery_rate_ssml(gui, tmp_path, monkeypatch):
    import io
    from vrchat_speech_assistant import providers
    monkeypatch.setattr(providers, "VOICES_PATH", tmp_path)
    monkeypatch.setattr(providers, "read_ogg_file", Mock())
    polly = providers.Polly.__new__(providers.Polly)
    polly.client = Mock()
    polly.client.synthesize_speech.return_value = {"AudioStream": io.BytesIO(b"audio")}
    polly.speech("Hello", "Justin", "Cable", {"rate": 85, "whispered": True})
    ssml = polly.client.synthesize_speech.call_args.kwargs["Text"]
    assert '<prosody rate="85%">' in ssml
    assert 'name="whispered"' in ssml


def test_missing_audio_api_does_not_prevent_startup(gui, monkeypatch):
    app, main = gui
    monkeypatch.setattr(main, "get_devices", Mock(side_effect=AttributeError("No WASAPI device")))
    assert main.VRCSpeechAssistantWindow._detect_devices("output") == []


def test_preview_countdown_auto_send(gui, window):
    from PySide6.QtTest import QTest
    app, main = gui
    window.preview_checkbox.setChecked(True)
    window.preview_delay.setValue(.1)
    window._submit_recognized("Hello preview", window.recognition_epoch)
    assert window.pending_draft
    assert window.manual_text.toPlainText() == "Hello preview"
    window.speech_provider.speech.assert_not_called()
    QTest.qWait(200)
    wait_output(app, window)
    assert window.speech_provider.speech.call_args.args[0] == "Hello preview"


def test_edit_pauses_preview_and_keeps_later_recognition_out(gui, window):
    from PySide6.QtTest import QTest
    app, main = gui
    window.preview_checkbox.setChecked(True)
    window.preview_delay.setValue(.1)
    window._submit_recognized("wrong nickname")
    window.edit_message_button.click()
    window.manual_text.setPlainText("Correct nickname")
    window._submit_recognized("must not overwrite")
    QTest.qWait(200)
    window.speech_provider.speech.assert_not_called()
    assert window.manual_text.toPlainText() == "Correct nickname"
    window.speak_button.click()
    wait_output(app, window)
    assert window.speech_provider.speech.call_args.args[0] == "Correct nickname"


def test_stop_cancels_preview_and_late_recognition(gui, window):
    app, main = gui
    window.preview_checkbox.setChecked(True)
    window._submit_recognized("Keep draft")
    old_epoch = window.recognition_epoch
    window.stop_speaking()
    window._submit_recognized("Old recognition result", old_epoch)
    assert not window.preview_timer.isActive()
    assert not window.pending_draft
    assert window.manual_text.toPlainText() == "Keep draft"
    window.speech_provider.speech.assert_not_called()


def test_stop_during_speech_prevents_chatbox_and_next_output_works(gui, window, monkeypatch):
    import threading
    from vrchat_speech_assistant.output_control import check_cancelled
    app, main = gui
    entered = threading.Event()
    def speak(*args):
        entered.set()
        while True:
            check_cancelled()
            time.sleep(.01)
    window.speech_provider.speech.side_effect = speak
    chatbox = Mock()
    monkeypatch.setattr(main, "write_chatbox", chatbox)
    window.manual_chatbox.setChecked(True)
    window.manual_text.setPlainText("long message")
    window.speak_manual_text()
    assert entered.wait(1)
    window.roleplay_action("stop_speaking")
    wait_output(app, window)
    chatbox.assert_not_called()
    window.speech_provider.speech.side_effect = None
    window.manual_text.setPlainText("new message")
    window.speak_manual_text()
    wait_output(app, window)
    assert chatbox.call_args.args[1] == "new message"


def test_language_hotkey_switches_both_and_restores_voice(gui, window, monkeypatch):
    app, main = gui
    window.config["LANGUAGES"].update(first="English", second="Polish")
    window.config["SPEECH"].update(source_language="English", target_language="English", provider="Windows Speech")
    window.windows_speech = Mock(voices={"Microsoft David English": "en", "Microsoft Paulina Polish": "pl"})
    window._append_voices_for_selected_provider()
    window.speech_voice_combo.setCurrentText("Microsoft David English")
    window.roleplay_action("switch_language")
    assert window.config["SPEECH"]["source_language"] == "Polish"
    assert window.config["SPEECH"]["target_language"] == "Polish"
    assert window.speech_voice_combo.currentText() == "Microsoft Paulina Polish"
    window.roleplay_action("switch_language")
    assert window.speech_voice_combo.currentText() == "Microsoft David English"
    assert window.config["SPEECH"]["source_language"] == "English"


def test_reconnect_preserves_routing_and_resumes_only_requested_listener(gui, window, monkeypatch):
    import threading
    app, main = gui
    window.listener_session = Mock()
    window.listener_session.thread.is_alive.return_value = False
    window.listener = Mock()
    window.is_listener_running = True
    window._apply_devices([], [])
    assert window.recover_listener and not window.is_listener_running
    assert window.config["SPEECH"]["output_device"] == "Test device"
    start = Mock()
    monkeypatch.setattr(window, "start_listener", start)
    window._apply_devices([{"name": "Test device", "index": 5}], [{"name": "Test device", "index": 8}])
    start.assert_called_once()
    window.stop_listener()  # Explicit cancellation must disable recovery.
    start.reset_mock()
    window._apply_devices([{"name": "Test device", "index": 5}], [{"name": "Test device", "index": 8}])
    start.assert_not_called()


def test_stale_capture_failure_cannot_restart_cancelled_listener(gui, window):
    import threading
    app, main = gui
    session = Mock(stopped=threading.Event())
    window.listener_session = session
    session.stopped.set()
    window._capture_failed(OSError("old failure"), session)
    assert not window.recover_listener


def test_clearing_an_unsent_editor_resumes_recognition(gui, window):
    window.manual_text.setPlainText("unsent manual text")
    window._submit_recognized("blocked")
    assert window.manual_text.toPlainText() == "unsent manual text"
    window.manual_text.clear()
    window.preview_checkbox.setChecked(True)
    window._submit_recognized("new recognition")
    assert window.manual_text.toPlainText() == "new recognition"


def test_missing_output_blocks_cloud_and_preserves_draft(gui, window, monkeypatch):
    window.output_devices = []
    window.manual_text.setPlainText("do not send yet")
    monkeypatch.setattr(window, "refresh_devices", Mock())
    window.speak_manual_text()
    window.speech_provider.speech.assert_not_called()
    assert window.editor_dirty
    assert window.manual_text.toPlainText() == "do not send yet"


def test_language_shortcut_remembers_existing_piper_model(gui, window):
    window.config["LANGUAGES"].update(first="English", second="Polish")
    window.config["SPEECH"].update(provider="Piper (offline)", source_language="English", target_language="English",
                                   piper_model="english.onnx", piper_model_Polish="polish.onnx")
    window.switch_language()
    assert window.config["SPEECH"]["piper_model"] == "polish.onnx"
    window.switch_language()
    assert window.config["SPEECH"]["piper_model"] == "english.onnx"


def test_capture_failures_back_off_before_reopening_device(gui, window, monkeypatch):
    import threading
    app, main = gui
    session = Mock(stopped=threading.Event())
    session.thread.is_alive.return_value = False
    window.listener_session = session
    monkeypatch.setattr(window, "refresh_devices", Mock())
    start = Mock()
    monkeypatch.setattr(window, "start_listener", start)
    window._capture_failed(OSError("device failed but is still listed"), session)
    available = [{"name": "Test device", "index": 0}]
    window._apply_devices(available, available)
    start.assert_not_called()
    window.capture_retry_after = 0
    window._apply_devices(available, available)
    start.assert_called_once()
