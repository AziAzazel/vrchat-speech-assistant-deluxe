"""Retain generated files before temporary cleanup and export original bytes."""
from pathlib import Path
from unittest.mock import Mock
import threading
import wave
import pytest
from vrchat_speech_assistant.audio_export import read_generated_audio, save_generated_audio, GeneratedAudio, AudioRetentionError
from vrchat_speech_assistant.output_control import generated_audio_scope, report_generated_audio, OutputCancelled


def make_wav(path):
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1,2,22050,0,'NONE','not compressed'))
        audio.writeframes(b'\0\0'*100)
    return path.read_bytes()


def test_original_audio_survives_temp_deletion_and_saves_atomically(tmp_path):
    source = tmp_path/'generated.wav'
    data = make_wav(source)
    clip = read_generated_audio(source)
    source.unlink()
    target = tmp_path/'export.wav'
    save_generated_audio(clip, target)
    assert target.read_bytes() == data
    with pytest.raises(ValueError):
        save_generated_audio(clip, tmp_path/'wrong.mp3')
    assert not (tmp_path/'wrong.mp3').exists()


def test_failed_save_preserves_existing_file_and_cleans_temporary(monkeypatch, tmp_path):
    import vrchat_speech_assistant.audio_export as export
    target = tmp_path/'export.wav'
    target.write_bytes(b'original')
    monkeypatch.setattr(export.os, 'replace', Mock(side_effect=OSError('failure')))
    with pytest.raises(OSError):
        save_generated_audio(GeneratedAudio('.wav', b'new'), target)
    assert target.read_bytes() == b'original'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['export.wav']


def test_retention_is_bounded_and_rejects_unknown_format(monkeypatch, tmp_path):
    import vrchat_speech_assistant.audio_export as export
    source = tmp_path/'file'
    source.write_bytes(b'not audio')
    with pytest.raises(AudioRetentionError): read_generated_audio(source)
    monkeypatch.setattr(export, 'MAX_AUDIO_BYTES', 8)
    source.write_bytes(b'OggS12345')
    with pytest.raises(AudioRetentionError): read_generated_audio(source)


def test_capture_scope_does_not_leak_after_exception_or_to_other_threads():
    capture = Mock()
    with pytest.raises(OutputCancelled), generated_audio_scope(capture):
        report_generated_audio('own.wav')
        other = threading.Thread(target=lambda: report_generated_audio('other.wav'))
        other.start(); other.join()
        raise OutputCancelled()
    report_generated_audio('outside.wav')
    capture.assert_called_once_with('own.wav')


@pytest.mark.parametrize('backend', ['windows', 'piper'])
def test_local_backend_retains_before_playback_and_temporary_cleanup(gui, monkeypatch, tmp_path, backend):
    from vrchat_speech_assistant import providers
    from vrchat_speech_assistant.windows_speech import WindowsSpeech
    from vrchat_speech_assistant.piper_speech import PiperSpeech
    provider = WindowsSpeech.__new__(WindowsSpeech) if backend == 'windows' else PiperSpeech('model')
    generated = []
    def render(*args, **kwargs):
        path = Path(args[2] if backend == 'windows' else args[1])
        generated.append((path, make_wav(path)))
    monkeypatch.setattr(provider, 'render', render)
    player = Mock()
    monkeypatch.setattr(providers, 'read_ogg_file', player)
    clips = []
    with generated_audio_scope(lambda path: clips.append(read_generated_audio(path))):
        provider.speech('Hello', 'voice', 'device', {'rate':85})
    assert clips[0].data == generated[0][1]
    assert not generated[0][0].exists()
    player.assert_called_once()


def test_cached_polly_exports_original_ogg_without_another_request(monkeypatch, tmp_path):
    from vrchat_speech_assistant import providers
    monkeypatch.setattr(providers, 'VOICES_PATH', tmp_path)
    cloud = providers.Polly.__new__(providers.Polly)
    import io
    cloud.client = Mock()
    cloud.client.synthesize_speech.return_value = {'AudioStream': io.BytesIO(b'OggSoriginal-audio')}
    monkeypatch.setattr(providers, 'read_ogg_file', Mock())
    clips = []
    with generated_audio_scope(lambda path: clips.append(read_generated_audio(path))):
        cloud.speech('Hello', 'Mizuki', 'device', {'whispered':True})
        cloud.speech('Hello', 'Mizuki', 'device', {'whispered':True})
    cloud.client.synthesize_speech.assert_called_once()
    assert clips[0] == clips[1] == GeneratedAudio('.ogg', b'OggSoriginal-audio')
    target = tmp_path/'saved.ogg'
    save_generated_audio(clips[1], target)
    cloud.client.synthesize_speech.assert_called_once()
    assert target.read_bytes() == b'OggSoriginal-audio'
