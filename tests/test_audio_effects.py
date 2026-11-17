"""Measure the audible effect, duration, export and provider requests."""
import io
from pathlib import Path
import threading
from unittest.mock import Mock

import numpy as np
import pytest
import soundfile as sf

from vrchat_speech_assistant.audio_effects import shift_pitch, pitched_audio
from vrchat_speech_assistant.audio_export import read_generated_audio, save_generated_audio
from vrchat_speech_assistant.output_control import generated_audio_scope, output_scope, OutputCancelled


def tone(rate=22050, seconds=3):
    clock = np.arange(round(rate * seconds)) / rate
    return np.column_stack((.25 * np.sin(2 * np.pi * 440 * clock),
                            .25 * np.sin(2 * np.pi * 660 * clock)))


def frequency(samples, rate):
    middle = samples[len(samples)//3:2*len(samples)//3]
    return np.argmax(abs(np.fft.rfft(middle * np.hanning(len(middle))))) * rate / len(middle)


@pytest.mark.parametrize('pitch', [-75, -50, -20, 0, 50, 100, 300])
def test_pitch_changes_frequency_without_changing_duration_or_channels(pitch):
    source = tone()
    result = shift_pitch(source, pitch)
    assert result.shape == source.shape
    assert np.isfinite(result).all() and abs(result).max() <= 1
    for channel, original in enumerate((440, 660)):
        assert frequency(result[:, channel], 22050) == pytest.approx(original * (1 + pitch/100), abs=2)
    assert np.sqrt(np.mean(result ** 2)) > .02
    if pitch == 0:
        np.testing.assert_array_equal(source, result)


@pytest.mark.parametrize('count', [1, 50, 511, 2048])
def test_silence_and_short_clips_remain_finite(count):
    result = shift_pitch(np.zeros((count, 1)), 300)
    assert result.shape == (count, 1)
    assert not result.any()


def test_pitch_can_be_cancelled_before_processing():
    event = threading.Event()
    event.set()
    with output_scope(event), pytest.raises(OutputCancelled):
        shift_pitch(tone(), 100)


@pytest.mark.parametrize('backend', ['standard', 'neural', 'windows', 'piper'])
def test_every_backend_plays_and_exports_the_processed_audio(monkeypatch, tmp_path, backend):
    from vrchat_speech_assistant import providers
    from vrchat_speech_assistant.windows_speech import WindowsSpeech
    from vrchat_speech_assistant.piper_speech import PiperSpeech
    original = tone(seconds=1)
    played, retained = [], []
    def play(path, device):
        assert device == 'device'
        played.append(Path(path).read_bytes())
    monkeypatch.setattr(providers, 'read_ogg_file', play)
    monkeypatch.setattr(providers, 'VOICES_PATH', tmp_path/'cache')
    if backend in ('standard', 'neural'):
        encoded = io.BytesIO()
        sf.write(encoded, original, 22050, format='OGG', subtype='VORBIS')
        provider = providers.Polly.__new__(providers.Polly)
        provider.client = Mock()
        provider.client.synthesize_speech.side_effect = lambda **kw: {'AudioStream': io.BytesIO(encoded.getvalue())}
        voice = 'Justin' if backend == 'standard' else 'Ola [Neural]'
    else:
        provider = WindowsSpeech.__new__(WindowsSpeech) if backend == 'windows' else PiperSpeech('model')
        def render(*args, **kwargs):
            path = args[2] if backend == 'windows' else args[1]
            sf.write(str(path), original, 22050)
        monkeypatch.setattr(provider, 'render', render)
        voice = 'voice'
    with generated_audio_scope(lambda path: retained.append(read_generated_audio(path))):
        provider.speech('Private text', voice, 'device', {'pitch': 100, 'rate': 85})
    target = tmp_path/'export.wav'
    save_generated_audio(retained[0], target)
    assert target.read_bytes() == played[0]
    processed, rate = sf.read(target, always_2d=True)
    assert rate == 22050 and processed.shape == original.shape
    assert frequency(processed[:, 0], rate) == pytest.approx(880, abs=4)
    if backend in ('standard', 'neural'):
        request = provider.client.synthesize_speech.call_args.kwargs
        assert 'pitch=' not in request['Text'] and 'whispered' not in request['Text']
        assert request['Engine'] == backend
        provider.speech('Private text', voice, 'device', {'pitch': -50, 'rate': 85})
        assert provider.client.synthesize_speech.call_count == 1


def test_processed_temporary_file_is_removed_without_changing_original(tmp_path):
    path = tmp_path/'source.wav'
    sf.write(path, tone(seconds=.2), 22050)
    original = path.read_bytes()
    with pitched_audio(path, {'pitch': -50}) as processed:
        assert processed != path and processed.is_file()
    assert not processed.exists() and path.read_bytes() == original
