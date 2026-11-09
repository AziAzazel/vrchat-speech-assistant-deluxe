import subprocess
import wave
from unittest.mock import Mock

import pytest
from vrchat_speech_assistant.piper_speech import PiperSpeech
from vrchat_speech_assistant.windows_speech import LocalSynthesisError
from vrchat_speech_assistant.text_tools import decorate_chatbox


def test_keyword_boundaries_translation_and_no_cascade():
    assert decorate_chatbox("Hello, friend!", {"hello": "👋", "he": "NO"}) == "Hello, friend! 👋"
    assert decorate_chatbox("Bonjour", {"hello": "👋"}, "Hello") == "Bonjour 👋"
    assert decorate_chatbox("hello", {"hello": "robot", "robot": "🤖"}) == "hello robot"
    assert decorate_chatbox("hello hi", {"hello": "👋", "hi": "👋"}) == "hello hi 👋"
    assert decorate_chatbox("a+b!", {"a+b": "image-link"}) == "a+b! image-link"


@pytest.mark.parametrize("rate", [85, 100, 115])
def test_piper_cli_and_unicode_input(tmp_path, monkeypatch, rate):
    model = tmp_path / "my voice.onnx"
    model.write_bytes(b"model")
    (tmp_path / "my voice.onnx.json").write_text("{}")
    target = tmp_path / "speech.wav"
    def run(argv, **kwargs):
        assert argv[1:3] == ["-m", "piper"]
        assert kwargs["input"] == 'café & "hello" 👋'
        assert kwargs["check"] and kwargs["timeout"] == 120
        assert "shell" not in kwargs
        assert kwargs["encoding"] == "utf-8"
        assert float(argv[argv.index("--length-scale") + 1]) == pytest.approx(100 / rate)
        assert str(model) in argv
        assert kwargs["input"] not in argv
        with wave.open(str(target), "wb") as audio:
            audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
            audio.writeframes(b"\0\0" * 100)
    monkeypatch.setattr(subprocess, "run", run)
    PiperSpeech(str(model)).render('café & "hello" 👋', target, rate=rate)


def test_piper_missing_assets_never_launches_process(tmp_path, monkeypatch):
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(LocalSynthesisError):
        PiperSpeech("").render("hello", tmp_path / "out.wav")
    run.assert_not_called()


def test_piper_timeout_becomes_synthesis_failure(tmp_path, monkeypatch):
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"model")
    (tmp_path / "voice.onnx.json").write_text("{}")
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=subprocess.TimeoutExpired("piper", 120)))
    with pytest.raises(LocalSynthesisError):
        PiperSpeech(str(model)).render("hello", tmp_path / "out.wav")


def test_standalone_piper_uses_external_backend(tmp_path, monkeypatch):
    import sys
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"model")
    (tmp_path / "voice.onnx.json").write_text("{}")
    backend = tmp_path / "piper.exe"
    backend.write_bytes(b"external tool")
    target = tmp_path / "out.wav"
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        with wave.open(str(target), "wb") as audio:
            audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
            audio.writeframes(b"\0\0" * 10)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(subprocess, "run", run)
    PiperSpeech(str(model), str(backend)).render("hello", target)
    assert calls[0][0] == str(backend)
    assert "-m" not in calls[0]
