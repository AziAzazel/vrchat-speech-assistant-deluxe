import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock
import pytest
from vrchat_speech_assistant.output_control import OutputCancelled, output_scope, run_process


def test_cancellation_kills_running_piper_process():
    event = threading.Event()
    timer = threading.Timer(.15, event.set)
    timer.start()
    try:
        with output_scope(event), pytest.raises(OutputCancelled):
            run_process([sys.executable, "-c", "import time; time.sleep(10)"],
                        input="hello", encoding="utf-8", stdout=-1, stderr=-1, check=True, timeout=20)
    finally:
        timer.cancel()


def test_cancelled_fallback_never_contacts_cloud():
    from vrchat_speech_assistant.windows_speech import SpeechWithFallback, LocalSynthesisError
    event = threading.Event()
    primary, factory = Mock(), Mock()
    def fail(*args):
        event.set()
        raise LocalSynthesisError()
    primary.speech.side_effect = fail
    with output_scope(event), pytest.raises(OutputCancelled):
        SpeechWithFallback(primary, factory, "Justin", Mock()).speech("hi", "local", "Cable")
    factory.assert_not_called()


def test_fresh_device_enumeration_terminates_portaudio(monkeypatch):
    from vrchat_speech_assistant.audio_devices import _get_devices_in_probe
    context = Mock()
    context.get_host_api_info_by_type.return_value = {"index": 1}
    context.get_device_count.return_value = 2
    context.get_device_info_by_index.side_effect = [
        {"name": "Cable", "hostApi": 1, "index": 0, "maxOutputChannels": 2},
        {"name": "Speakers", "hostApi": 2, "index": 1, "maxOutputChannels": 2}]
    monkeypatch.setitem(sys.modules, "pyaudio", SimpleNamespace(PyAudio=lambda: context, paMME=1, paWASAPI=2))
    assert _get_devices_in_probe("output")[0]["name"] == "Cable"
    context.terminate.assert_called_once()


def test_capture_failure_is_reported_and_stream_closes():
    from vrchat_speech_assistant.listener import BackgroundListener
    microphone, recognizer, failure = MagicMock(), Mock(), Mock()
    recognizer.listen.side_effect = OSError("disconnected")
    listener = BackgroundListener(recognizer, microphone, Mock(), failure)
    listener.start()
    listener.thread.join(timeout=1)
    assert not listener.thread.is_alive()
    failure.assert_called_once()
    microphone.__exit__.assert_called_once()
