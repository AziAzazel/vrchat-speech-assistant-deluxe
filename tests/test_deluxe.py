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
    window.ending_frequency.setValue(0)
    window.speech_provider = Mock()
    yield window
    # A draft left by a test must not auto-send while the fixture is closing.
    window.preview_timer.stop()
    window.countdown_timer.stop()
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
    settings["global_hotkeys"] = "False"  # This test exercises Qt's app-scoped shortcut signal.
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
    assert len(window.shortcuts) == 10 + sum(bool(preset["key"]) for preset in window.soundboard_presets)
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
    monkeypatch.setattr(main, "get_device_snapshot", Mock(side_effect=RuntimeError("probe failed")))
    assert main.VRCSpeechAssistantWindow._detect_device_snapshot() == (None, None)


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


def test_stop_during_speech_keeps_first_caption_and_next_output_works(gui, window, monkeypatch):
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
    chatbox.assert_called_once()
    assert chatbox.call_args.args[1] == "long message"
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


def test_manual_language_dropdown_restores_nonfirst_voice(gui, window, monkeypatch):
    app, main = gui
    window.config["SPEECH"]["provider"] = "Amazon Polly"
    english, polish = ["English first", "English chosen"], ["Polish first", "Polish chosen"]
    monkeypatch.setitem(main.VOICES["polly"], "English", english)
    monkeypatch.setitem(main.VOICES["polly"], "Polish", polish)
    window.target_language_combo.setCurrentText("English")
    window._append_voices_for_selected_provider()
    window.speech_voice_combo.setCurrentText("English chosen")
    window.target_language_combo.setCurrentText("Polish")
    window.speech_voice_combo.setCurrentText("Polish chosen")
    window.target_language_combo.setCurrentText("English")
    assert window.speech_voice_combo.currentText() == "English chosen"
    window.target_language_combo.setCurrentText("Polish")
    assert window.speech_voice_combo.currentText() == "Polish chosen"


def test_voice_choices_are_separate_per_provider(gui, window, monkeypatch):
    app, main = gui
    window.windows_speech = Mock(voices={"SAPI first": "1", "SAPI chosen": "2"})
    monkeypatch.setitem(main.VOICES["polly"], "English", ["Polly first", "Polly chosen"])
    window.target_language_combo.setCurrentText("English")
    window.speech_provider_combo.setCurrentText("Windows Speech")
    window._append_voices_for_selected_provider()
    window.speech_voice_combo.setCurrentText("SAPI chosen")
    window.speech_provider_combo.setCurrentText("Amazon Polly")
    window.speech_voice_combo.setCurrentText("Polly chosen")
    window.speech_provider_combo.setCurrentText("Windows Speech")
    assert window.speech_voice_combo.currentText() == "SAPI chosen"
    window.speech_provider_combo.setCurrentText("Amazon Polly")
    assert window.speech_voice_combo.currentText() == "Polly chosen"


def test_pitch_and_window_size_survive_restart(gui, window, monkeypatch):
    app, main = gui
    window.speech_pitch_slider.setValue(-23)
    window.resize(700, 620)
    window._save_window_size()
    window.close()
    restarted = main.VRCSpeechAssistantWindow()
    try:
        assert restarted.speech_pitch_slider.value() == -23
        assert restarted.extra_tags["pitch"] == -23
        assert restarted.width() == 700 and restarted.height() == 620
        assert restarted.config["SPEECH"]["pitch"] == "-23"
        restarted.speech_pitch_slider.setValue(0)  # Avoid affecting later tests.
    finally:
        restarted.close()


def test_cards_reflow_and_labels_wrap(gui, window):
    app, main = gui
    window.show()
    window.resize(650, 700)
    app.processEvents()
    assert window.responsive_cards.columns == 1
    window.resize(1100, 700)
    app.processEvents()
    assert window.responsive_cards.columns == 2
    window.resize(1500, 700)
    app.processEvents()
    assert window.responsive_cards.columns == 3
    assert window.hotkey_state_label.wordWrap()
    assert window.log_line_edit.wordWrap()
    assert window.toggle_activate_button.maximumWidth() > 1000


def test_legacy_focus_only_settings_migrate_once(gui, window, tmp_path, monkeypatch):
    app, main = gui
    window.close()
    settings = tmp_path / "legacy.ini"
    settings.write_text("[ROLEPLAY]\nglobal_hotkeys = False\n", encoding="utf-8")
    monkeypatch.setattr(main, "CONFIG_FILE", settings)
    legacy = main.VRCSpeechAssistantWindow()
    try:
        assert legacy.config["ROLEPLAY"].getboolean("global_hotkeys")
        assert legacy.global_shortcuts_checkbox.isChecked()
        legacy.global_shortcuts_checkbox.setChecked(False)
    finally:
        legacy.close()
    opted_out = main.VRCSpeechAssistantWindow()
    try:
        assert not opted_out.config["ROLEPLAY"].getboolean("global_hotkeys")
    finally:
        opted_out.close()


def test_pronunciation_and_random_ending_after_translation(gui, window, monkeypatch):
    app, main = gui
    chatbox = Mock()
    monkeypatch.setattr(main, "write_chatbox", chatbox)
    window.config["ROLEPLAY"].update(chatbox_tag="False", delivery="Normal")
    window.pronunciations = {"Nekosan": "Neko-san"}
    window.config["SPEECH"].update(source_language="English", target_language="French")
    window.translator = Mock()
    window.translator.translate_text.return_value.text = "Bonjour Nekosan!"
    window.ending_text.setText(", desu")
    window.ending_frequency.setValue(100)
    window.manual_chatbox.setChecked(True)
    window.manual_text.setPlainText("Hello Nekosan!")
    window.speak_manual_text()
    wait_output(app, window)
    assert window.speech_provider.speech.call_args.args[0] == "Bonjour Neko-san, desu!"
    assert chatbox.call_args.args[1] == "Bonjour Nekosan, desu!"
    entry = window.history[-1]
    assert entry["source"] == "Hello Nekosan!"
    assert entry["spoken"] == "Bonjour Neko-san, desu!"
    assert entry["status"] == "completed"
    window.ending_text.setText(", poi")
    assert window.replay_history(entry)
    wait_output(app, window)
    assert window.translator.translate_text.call_count == 1
    assert chatbox.call_args.args[1] == "Bonjour Nekosan, desu!"
    assert window.history[-1]["result"] == entry["result"]


def test_history_is_bounded_clearable_and_load_does_not_overwrite_draft(gui, window):
    from vrchat_speech_assistant.history_dialog import HistoryDialog
    for index in range(60):
        window._record_history({"id": index, "time": "12:00:00", "status": "completed", "language": "English",
                                "source": f"Original {index}", "result": f"Result {index}", "spoken": f"Spoken {index}",
                                "provider": "Windows Speech", "voice": "Local"})
    assert len(window.history) == 50 and window.history[0]["id"] == 10
    dialog = HistoryDialog(window)
    try:
        assert dialog.table.rowCount() == 50
        assert dialog.selected()["id"] == 59
        window.manual_text.setPlainText("unsent draft")
        assert not window.load_history_source(dialog.selected())
        assert window.manual_text.toPlainText() == "unsent draft"
        window.manual_text.clear()
        dialog.load_button.click()
        assert window.manual_text.toPlainText() == "Original 59"
        assert window.editor_dirty
        window.clear_history()
        assert not window.history
    finally:
        dialog.close()


def test_history_marks_cancelled_and_failed_output(gui, window):
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
    window.manual_text.setPlainText("stop this")
    window.speak_manual_text()
    assert entered.wait(1)
    window.stop_speaking()
    wait_output(app, window)
    assert window.history[-1]["status"] == "cancelled"
    window.speech_provider.speech.side_effect = RuntimeError("provider failure")
    window.manual_text.setPlainText("failed output")
    window.speak_manual_text()
    wait_output(app, window)
    assert window.history[-1]["status"] == "failed"


def test_whole_category_and_ending_preferences_survive_restart(gui, window):
    app, main = gui
    window.cards_by_key["inputs"].set_collapsed(True)
    window.cards_by_key["voice"].set_collapsed(False)
    window.ending_text.setText(", poi")
    window.ending_frequency.setValue(37)
    window.close()
    restarted = main.VRCSpeechAssistantWindow()
    try:
        assert restarted.cards_by_key["inputs"].is_collapsed()
        assert not restarted.cards_by_key["voice"].is_collapsed()
        assert restarted.ending_text.text() == ", poi"
        assert restarted.ending_frequency.value() == 37
        assert not restarted.history  # History is never persisted.
        restarted.ending_frequency.setValue(0)
    finally:
        restarted.close()


def test_preview_expands_message_category(gui, window):
    window.cards_by_key["messages"].set_collapsed(True)
    window.preview_checkbox.setChecked(True)
    window._submit_recognized("Edit me")
    assert not window.cards_by_key["messages"].is_collapsed()
    assert window.manual_text.toPlainText() == "Edit me"


def test_pronunciation_editor_saves_persistent_rules(gui, window, monkeypatch, tmp_path):
    app, main = gui
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    def accept_dictionary(dialog):
        table = dialog.findChild(main.QtWidgets.QTableWidget)
        table.setRowCount(1)
        table.setItem(0, 0, main.QtWidgets.QTableWidgetItem("Nekosan"))
        table.setItem(0, 1, main.QtWidgets.QTableWidgetItem("Neko-san"))
        return main.QtWidgets.QDialog.Accepted
    monkeypatch.setattr(main.QtWidgets.QDialog, "exec", accept_dictionary)
    window.edit_pronunciations()
    assert window.pronunciations == {"Nekosan": "Neko-san"}
    assert 'Neko-san' in (tmp_path / 'pronunciation.json').read_text()
    window._init_config()
    assert window.pronunciations == {"Nekosan": "Neko-san"}


def test_neural_voice_keeps_pitch_setting_and_explains_invalid_style(gui, window, monkeypatch):
    app, main = gui
    window.config['SPEECH'].update(provider='Amazon Polly', target_language='Polish')
    window.config['ROLEPLAY']['delivery'] = 'Normal'
    window.target_language_combo.blockSignals(True)
    window.target_language_combo.setCurrentText('Polish')
    window.target_language_combo.blockSignals(False)
    window._append_voices_for_selected_provider()
    window.speech_voice_combo.setCurrentText('Ola [Neural]')
    assert 'Neural' in window.polly_capability_label.text()
    window.speech_pitch_slider.setValue(-20)
    window.manual_text.setPlainText('Cześć')
    window.speak_manual_text()
    app.processEvents()
    window.speech_provider.speech.assert_not_called()
    assert 'Standard voice' in window.log_line_edit.text()
    assert window.config['SPEECH']['pitch'] == '-20'
    window.speech_pitch_slider.setValue(0)


def test_failed_scan_preserves_devices_listener_and_allows_retry(gui, window, monkeypatch):
    app, main = gui
    window.device_scan_busy = True
    window.is_listener_running = True
    before = window.input_devices, window.output_devices
    stop = Mock()
    monkeypatch.setattr(window, 'stop_listener', stop)
    window._apply_devices(None, None)
    assert (window.input_devices, window.output_devices) == before
    assert window.is_listener_running and not window.device_scan_busy
    stop.assert_not_called()
    assert 'keeping the last device list' in window.log_line_edit.text()


@pytest.mark.parametrize('mode,speech_expected,chatbox_expected', [
    ('Voice only', True, False), ('Chatbox only', False, True), ('Voice + chatbox', True, True)])
def test_soundboard_routes_exact_phrase_without_changing_language(gui, window, monkeypatch, mode, speech_expected, chatbox_expected):
    from vrchat_speech_assistant.soundboard import DEFAULT_PRESETS
    app, main = gui
    window.config['API'].update(aws_access_key='test-access', aws_secret_key='test-secret')
    window.config['SPEECH'].update(source_language='Polish', target_language='English', enabled='False')
    window.config['CHATBOX']['enabled'] = 'False'
    window.config['ROLEPLAY'].update(delivery='Confidential whisper', chatbox_tag='True')
    window.extra_tags = {'whispered': True, 'pitch': -20}
    window.config['ENDING'].update(text=', desu', frequency='100')
    window.pronunciations = {'ぽい': 'wrong'}
    window.manual_text.setPlainText('Keep this draft')
    window.translator = Mock()
    window.osc_client = Mock()
    chatbox, cloud = Mock(), Mock()
    monkeypatch.setattr(main, 'write_chatbox', chatbox)
    monkeypatch.setattr(main, 'Polly', Mock(return_value=cloud))
    preset = dict(DEFAULT_PRESETS[0], output=mode)
    before = dict(window.config['SPEECH'])
    assert window.play_soundboard(preset)
    wait_output(app, window)
    assert cloud.speech.called == speech_expected
    if speech_expected:
        cloud.speech.assert_called_once_with('ぽい', 'Mizuki', 'Test device', {})
    assert chatbox.called == chatbox_expected
    if chatbox_expected:
        assert chatbox.call_args.args[1] == 'ぽい'
    else:
        window.osc_client.send_message.assert_not_called()
    window.translator.translate_text.assert_not_called()
    window.speech_provider.speech.assert_not_called()
    assert dict(window.config['SPEECH']) == before
    assert window.manual_text.toPlainText() == 'Keep this draft'
    assert window.history[-1]['language'] == 'Japanese'


def test_soundboard_text_only_needs_no_voice_keys_or_audio_device(gui, window, monkeypatch):
    from vrchat_speech_assistant.soundboard import DEFAULT_PRESETS
    app, main = gui
    window.config['API'].update(aws_access_key='', aws_secret_key='')
    window.output_devices = []
    cloud, chatbox = Mock(), Mock()
    monkeypatch.setattr(main, 'Polly', cloud)
    monkeypatch.setattr(main, 'write_chatbox', chatbox)
    assert window.play_soundboard(dict(DEFAULT_PRESETS[0], output='Chatbox only', voice=''))
    wait_output(app, window)
    cloud.assert_not_called()
    assert chatbox.call_args.args[1] == 'ぽい'


def test_soundboard_busy_does_not_queue_or_replace_draft(gui, window):
    from vrchat_speech_assistant.soundboard import DEFAULT_PRESETS
    window.output_busy = True
    window.manual_text.setPlainText('draft')
    assert not window.play_soundboard(DEFAULT_PRESETS[0])
    assert window.manual_text.toPlainText() == 'draft'
    assert 'not queued' in window.log_line_edit.text()
    window.output_busy = False


def test_soundboard_dialog_persists_and_registers_shortcut(gui, window, monkeypatch):
    from vrchat_speech_assistant.soundboard_dialog import SoundboardDialog
    app, main = gui
    dialog = SoundboardDialog(window)
    assert dialog.table.cellWidget(0, 2).currentText() == 'Japanese'
    assert dialog.table.cellWidget(0, 5).currentText() == 'Mizuki'
    dialog.table.cellWidget(0, 3).setCurrentText('Chatbox only')
    dialog.save()
    window._init_config()
    assert window.soundboard_presets[0]['output'] == 'Chatbox only'
    if main.sys.platform != 'win32':
        assert any(shortcut.key().toString() == 'Ctrl+;' for shortcut in window.shortcuts)


def test_soundboard_hotkey_dispatch_uses_saved_row(gui, window, monkeypatch):
    play = Mock()
    monkeypatch.setattr(window, 'play_soundboard', play)
    window.roleplay_action('soundboard_0')
    play.assert_called_once_with(window.soundboard_presets[0])


@pytest.mark.parametrize('dialog_name', ['RoleplayDialog', 'SoundboardDialog'])
def test_record_shortcuts_while_own_bindings_are_suspended(gui, window, monkeypatch, dialog_name):
    from PySide6.QtTest import QTest
    from vrchat_speech_assistant.roleplay_dialog import RoleplayDialog
    from vrchat_speech_assistant.soundboard_dialog import SoundboardDialog
    app, main = gui
    window.config['ROLEPLAY']['global_hotkeys'] = 'False'
    window._init_hotkeys()
    dialog = {'RoleplayDialog': RoleplayDialog, 'SoundboardDialog': SoundboardDialog}[dialog_name](window)
    action = Mock()
    monkeypatch.setattr(window, 'play_soundboard', action)
    dialog.show()
    app.processEvents()
    assert window._hotkey_edit_depth == 1 and not window.shortcuts and window.global_hotkeys is None
    editor = dialog.table.cellWidget(0, 1 if dialog_name == 'RoleplayDialog' else 0)
    editor.setFocus()
    QTest.keyClick(editor, main.Qt.Key_Semicolon, main.Qt.ControlModifier)
    assert editor.keySequence().toString() == 'Ctrl+;'
    action.assert_not_called()
    QTest.keyClick(editor, main.Qt.Key_Backspace)
    assert editor.keySequence().isEmpty()
    dialog.reject()
    app.processEvents()
    assert window._hotkey_edit_depth == 0 and window.shortcuts


def test_recording_entry_preserves_paths_and_routes_no_cloud(gui, window, monkeypatch, tmp_path):
    from vrchat_speech_assistant.recording_dialog import RecordingDialog
    from vrchat_speech_assistant.soundboard_dialog import SoundboardDialog
    app, main = gui
    audio = tmp_path/'song.wav'
    audio.write_bytes(b'placeholder')
    srt = tmp_path/'song.srt'
    srt.write_text('1\n00:00:00,000 --> 00:00:02,000\nポイ', encoding='utf-8')
    dialog = SoundboardDialog(window)
    recording = RecordingDialog(dialog)
    recording.audio.setText(str(audio))
    recording.subtitle.setText(str(srt))
    recording.offset.setValue(300)
    recording.output.setCurrentText('Voice + chatbox')
    recording.save()
    assert recording.result_preset['offset_ms'] == 300
    dialog.add_row(recording.result_preset)
    preset = dialog.preset(dialog.table.rowCount()-1)
    assert preset['audio'] == str(audio) and preset['subtitle'] == str(srt)
    assert preset['kind'] == 'audio'
    cloud, start = Mock(), Mock(return_value=True)
    monkeypatch.setattr(main, 'Polly', cloud)
    monkeypatch.setattr(window, '_start_output', start)
    assert window.play_soundboard(preset)
    cloud.assert_not_called()
    assert start.call_args.kwargs['requires_audio']
    assert start.call_args.args[1] is False  # Subtitles are scheduled by the media backend.
    dialog.reject()


def test_text_only_output_survives_audio_device_disconnect(gui, window):
    window.output_busy = True
    window.output_requires_audio = False
    window._apply_devices([], [])
    assert not window.cancel_output.is_set()
    window.output_busy = False


def test_youtube_panel_stop_and_close_never_send_chatbox_or_synthesize(gui, window, monkeypatch):
    from vrchat_speech_assistant import youtube_dialog
    app, main = gui
    player = Mock(is_running=True)
    player.start.return_value = 'https://www.youtube.com/watch?v=abcdefghijk'
    monkeypatch.setattr(youtube_dialog, 'EdgePlayer', Mock(return_value=player))
    window.osc_client = Mock()
    window.open_youtube()
    panel = window.youtube_window
    panel.url.setText('https://youtu.be/abcdefghijk')
    panel.play()
    player.start.assert_called_once_with('https://youtu.be/abcdefghijk')
    window.osc_client.send_message.assert_not_called()
    window.speech_provider.speech.assert_not_called()
    window.stop_speaking()
    player.stop.assert_called_once()
    panel.close()
    assert player.stop.call_count == 2
    panel.timer.stop()


@pytest.mark.parametrize('name', ['speech_pitch_slider', 'ending_frequency'])
def test_dragged_slider_updates_live_but_persists_only_on_release(gui, window, monkeypatch, name):
    slider = getattr(window, name)
    commit = Mock(wraps=window._settings_store._commit)
    monkeypatch.setattr(window._settings_store, '_commit', commit)
    slider.setSliderDown(True)
    for value in (10, 20, 30):
        slider.setValue(value)
    commit.assert_not_called()
    slider.setSliderDown(False)
    assert commit.call_count == 1


def test_osc_dispatcher_belongs_to_window_and_does_not_keep_old_callbacks(gui, window):
    app, main = gui
    first = window.dispatcher
    window.close()
    other = main.VRCSpeechAssistantWindow()
    try:
        assert other.dispatcher is not first
        assert len(list(other.dispatcher.handlers_for_address('/pitch'))) == 1
    finally:
        other.close()


def test_caption_arrives_before_speech_finishes_and_animation_is_bypassed(gui, window, monkeypatch):
    import threading
    app, main = gui
    entered, release = threading.Event(), threading.Event()
    window.config['SPEECH'].update(enabled='True', provider='Windows Speech', voice='Test voice')
    window.config['ROLEPLAY'].update(delivery='Normal', chatbox_tag='False')
    window.config['CHATBOX']['font'] = 'Normal'
    order = []
    monkeypatch.setattr(main, 'write_chatbox', lambda *args, **kwargs: order.append(('text', args[1], kwargs)))
    def speak(*args):
        order.append(('audio', args[0]))
        entered.set()
        release.wait(2)
    window.speech_provider.speech.side_effect = speak
    window.config['CHATBOX']['animation'] = 'True'  # Legacy preference must not delay live pages.
    window.manual_chatbox.setChecked(True)
    window.manual_text.setPlainText('Visible immediately')
    try:
        window.speak_manual_text()
        assert entered.wait(1)
        assert order[0][0:2] == ('text', 'Visible immediately')
        assert order[0][2]['chunk_length'] == 0
        assert order[1][0] == 'audio'
    finally:
        release.set()
    wait_output(app, window)


def test_long_message_uses_one_synthesis_with_all_pages_during_playback(gui, window, monkeypatch):
    from vrchat_speech_assistant.output_control import playback_callback
    from vrchat_speech_assistant.live_chatbox import LiveChatbox
    app, main = gui
    clock = [0]
    sent = []
    window.config['SPEECH'].update(enabled='True', provider='Windows Speech', voice='Test voice')
    window.config['ROLEPLAY'].update(delivery='Normal', chatbox_tag='False')
    window.config['CHATBOX']['font'] = 'Normal'
    class FastCaptions(LiveChatbox):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, clock=lambda: clock[0], wait=lambda deadline: clock.__setitem__(0, max(clock[0], deadline)))
    monkeypatch.setattr(main, 'LiveChatbox', FastCaptions)
    monkeypatch.setattr(main, 'write_chatbox', lambda client, text, **kwargs: sent.append(text))
    source = ' '.join(f'word{index}' for index in range(150))
    def speech(*args):
        callback = playback_callback()
        assert sent and callback is not None
        for position in range(101):
            clock[0] = position
            callback(position, 100)
    window.speech_provider.speech.side_effect = speech
    window.manual_chatbox.setChecked(True)
    window.manual_text.setPlainText(source)
    window.speak_manual_text()
    wait_output(app, window)
    window.speech_provider.speech.assert_called_once()
    assert ' '.join(sent) == source
    assert all(len(page) <= 144 for page in sent)
