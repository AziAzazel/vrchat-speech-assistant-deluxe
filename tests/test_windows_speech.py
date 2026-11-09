"""SAPI/COM contract tests; real Windows integration still needs a Windows run."""
import contextlib
from pathlib import Path
from unittest.mock import Mock

import pytest

from vrchat_speech_assistant.windows_speech import (
    WindowsSpeech, SpeechWithFallback, LocalSynthesisError,
)


def test_local_success_never_creates_cloud_provider():
    primary, factory, notify = Mock(), Mock(), Mock()
    provider = SpeechWithFallback(primary, factory, "Justin", notify)
    provider.speech("hello", "Windows voice", "Cable", {})
    primary.speech.assert_called_once_with("hello", "Windows voice", "Cable", {})
    factory.assert_not_called()
    notify.assert_not_called()


def test_synthesis_failure_falls_back_with_separate_voice():
    primary, factory, notify = Mock(), Mock(), Mock()
    primary.speech.side_effect = LocalSynthesisError("unavailable")
    provider = SpeechWithFallback(primary, factory, "Justin", notify)
    provider.speech("hello", "Windows voice", "Cable", {"pitch": -10})
    factory.return_value.speech.assert_called_once_with("hello", "Justin", "Cable", {"pitch": -10})
    notify.assert_called_once()


def test_playback_failure_does_not_replay_online():
    primary, factory = Mock(), Mock()
    primary.speech.side_effect = OSError("audio device disconnected")
    with pytest.raises(OSError):
        SpeechWithFallback(primary, factory, "Justin", Mock()).speech("hello", "voice", "Cable")
    factory.assert_not_called()


@pytest.mark.parametrize("rate", [85, 100, 115])
def test_sapi_render_literal_text_and_cleanup(monkeypatch, tmp_path, rate):
    from vrchat_speech_assistant import windows_speech
    voice, token, stream = Mock(), Mock(), Mock()
    voice.GetVoices.return_value = [Mock(Id="token-id", GetDescription=Mock(return_value="Local voice"))]
    dispatch = Mock(side_effect=lambda name: {
        "SAPI.SpVoice": voice, "SAPI.SpObjectToken": token, "SAPI.SpFileStream": stream,
    }[name])
    exited = []

    @contextlib.contextmanager
    def session():
        try:
            yield dispatch
        finally:
            exited.append(True)
    monkeypatch.setattr(windows_speech, "sapi", session)
    provider = WindowsSpeech()
    assert provider.voices == {"Local voice": "token-id"}
    provider.render('<speak>"hello" & café</speak>', "Local voice", tmp_path / "speech.wav", rate=rate)
    assert voice.Rate == round((rate - 100) / 10)
    token.SetId.assert_called_once_with("token-id")
    stream.Open.assert_called_once_with(str(tmp_path / "speech.wav"), 3, False)
    voice.Speak.assert_called_once_with('<speak>"hello" & café</speak>', 16)
    stream.Close.assert_called_once()
    assert len(exited) == 2


def test_sapi_failure_closes_stream(monkeypatch, tmp_path):
    from vrchat_speech_assistant import windows_speech
    voice, token, stream = Mock(), Mock(), Mock()
    voice.Speak.side_effect = RuntimeError("SAPI failure")
    @contextlib.contextmanager
    def session():
        yield lambda name: {"SAPI.SpVoice": voice, "SAPI.SpObjectToken": token,
                            "SAPI.SpFileStream": stream}[name]
    monkeypatch.setattr(windows_speech, "sapi", session)
    provider = WindowsSpeech.__new__(WindowsSpeech)
    provider.voices = {"Local voice": "id"}
    with pytest.raises(LocalSynthesisError):
        provider.render("hello", "Local voice", tmp_path / "speech.wav")
    stream.Close.assert_called_once()


def test_wav_routed_to_selected_device_and_removed(gui, monkeypatch):
    from vrchat_speech_assistant import providers
    provider = WindowsSpeech.__new__(WindowsSpeech)
    provider.render = Mock(side_effect=lambda text, voice, path: path.write_bytes(b"wave data"))
    calls = []
    def playback(path, device):
        assert Path(path).read_bytes() == b"wave data"
        calls.append((path, device))
    monkeypatch.setattr(providers, "read_ogg_file", playback)
    provider.speech("hello", "voice", "Cable Input")
    assert calls[0][1] == "Cable Input"
    assert not Path(calls[0][0]).exists()


def test_com_initialized_and_released_on_error(monkeypatch):
    import sys
    import types
    from vrchat_speech_assistant.windows_speech import sapi
    com = Mock()
    client = types.ModuleType("win32com.client")
    client.Dispatch = Mock()
    monkeypatch.setitem(sys.modules, "pythoncom", com)
    monkeypatch.setitem(sys.modules, "win32com", types.ModuleType("win32com"))
    monkeypatch.setitem(sys.modules, "win32com.client", client)
    with pytest.raises(RuntimeError):
        with sapi() as dispatch:
            assert dispatch is client.Dispatch
            raise RuntimeError("failed")
    com.CoInitialize.assert_called_once()
    com.CoUninitialize.assert_called_once()


def test_sapi_cancellation_purges_and_never_falls_back(monkeypatch, tmp_path):
    import threading
    from vrchat_speech_assistant import windows_speech
    from vrchat_speech_assistant.output_control import output_scope, OutputCancelled
    voice, token, stream = Mock(), Mock(), Mock()
    event = threading.Event()
    def wait(milliseconds):
        event.set()
        return False
    voice.WaitUntilDone.side_effect = wait
    @contextlib.contextmanager
    def session():
        yield lambda name: {"SAPI.SpVoice": voice, "SAPI.SpObjectToken": token, "SAPI.SpFileStream": stream}[name]
    monkeypatch.setattr(windows_speech, "sapi", session)
    speech = WindowsSpeech.__new__(WindowsSpeech)
    speech.voices = {"Local": "id"}
    with output_scope(event), pytest.raises(OutputCancelled):
        speech.render("long sentence", "Local", tmp_path / "out.wav")
    assert voice.Speak.call_args_list[0].args == ("long sentence", 17)
    assert voice.Speak.call_args_list[-1].args == ("", 2)
    stream.Close.assert_called_once()
