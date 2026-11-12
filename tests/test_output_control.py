import sys
import threading
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
