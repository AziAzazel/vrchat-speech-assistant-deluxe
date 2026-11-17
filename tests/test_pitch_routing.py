"""Hybrid pitch boundaries, final exports and visible slider interaction."""
import io
import re
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import soundfile as sf
from PySide6 import QtCore, QtWidgets, QtTest

from vrchat_speech_assistant.pitch_routing import pitch_route
from vrchat_speech_assistant.providers import Polly
from vrchat_speech_assistant.output_control import generated_audio_scope
from vrchat_speech_assistant.audio_export import read_generated_audio, save_generated_audio


@pytest.mark.parametrize('pitch', [-75, -51, -50, -1, 0, 1, 50, 51, 300])
@pytest.mark.parametrize('provider,voice', [('Amazon Polly', 'Justin'), ('Amazon Polly', 'Ola [Neural]'),
                                          ('Windows Speech', 'Desktop'), ('Piper (offline)', 'model')])
def test_routing_matches_provider_capabilities_and_boundaries(provider, voice, pitch):
    expected = ('off' if pitch == 0 else 'ssml' if provider == 'Amazon Polly' and voice == 'Justin'
                and -50 <= pitch <= 50 else 'local')
    assert pitch_route(provider, voice, pitch) == expected


@pytest.mark.parametrize('pitch', [-51, -50, -20, 0, 20, 50, 51, 100])
@pytest.mark.parametrize('voice', ['Justin', 'Ola [Neural]'])
def test_polly_applies_pitch_once_and_exports_exact_played_audio(monkeypatch, tmp_path, pitch, voice):
    from vrchat_speech_assistant import providers
    monkeypatch.setattr(providers, 'VOICES_PATH', tmp_path/'cache')
    played, retained = [], []
    monkeypatch.setattr(providers, 'read_ogg_file', lambda path, device: played.append(Path(path).read_bytes()))
    def synthesize(**request):
        # Simulate AWS's audible SSML effect, then measure the final output so
        # accidental local processing on top of SSML fails this test.
        match = re.search(r'pitch="([+-]?\d+)%"', request['Text'])
        remote_pitch = int(match[1]) if match else 0
        data = .25*np.sin(2*np.pi*440*(1+remote_pitch/100)*np.arange(44100)/22050)
        stream = io.BytesIO()
        sf.write(stream, data, 22050, format='OGG', subtype='VORBIS')
        return {'AudioStream': io.BytesIO(stream.getvalue())}
    provider = Polly.__new__(Polly)
    provider.client = Mock()
    provider.client.synthesize_speech.side_effect = synthesize
    with generated_audio_scope(lambda path: retained.append(read_generated_audio(path))):
        provider.speech('Test <text>', voice, 'device', {'pitch': pitch, 'rate': 85})
    route = pitch_route('Amazon Polly', voice, pitch)
    request = provider.client.synthesize_speech.call_args.kwargs
    assert ('pitch=' in request['Text']) == (route == 'ssml')
    assert 'rate="85%"' in request['Text'] and '&lt;text&gt;' in request['Text']
    assert retained[0].extension == ('.wav' if route == 'local' else '.ogg')
    target = tmp_path/('export'+retained[0].extension)
    save_generated_audio(retained[0], target)
    assert target.read_bytes() == played[0]
    audio, rate = sf.read(target)
    middle = audio[rate//2:3*rate//2]
    frequency = np.argmax(abs(np.fft.rfft(middle*np.hanning(len(middle)))))
    assert frequency == pytest.approx(440*(1+pitch/100), abs=3)


def test_cache_separates_ssml_pitches_from_dry_local_audio(monkeypatch, tmp_path):
    from vrchat_speech_assistant import providers
    from contextlib import nullcontext
    monkeypatch.setattr(providers, 'VOICES_PATH', tmp_path)
    monkeypatch.setattr(providers, 'pitched_audio', lambda path, tags: nullcontext(path))
    monkeypatch.setattr(providers, 'read_ogg_file', Mock())
    provider = Polly.__new__(Polly)
    provider.client = Mock()
    provider.client.synthesize_speech.side_effect = lambda **kw: {'AudioStream': io.BytesIO(b'audio')}
    for pitch in (-20, -20, 20, 51, 100, 0):
        provider.speech('Same text', 'Justin', 'device', {'pitch': pitch})
    requests = provider.client.synthesize_speech.call_args_list
    assert len(requests) == 3
    assert 'pitch="-20%"' in requests[0].kwargs['Text']
    assert 'pitch="+20%"' in requests[1].kwargs['Text']
    assert 'pitch=' not in requests[2].kwargs['Text']


def test_slider_route_legend_zero_reset_and_precise_keyboard_steps(gui):
    from vrchat_speech_assistant.pitch_control import PitchControl, LOCAL_COLOR, SSML_COLOR
    app, _ = gui
    control = PitchControl()
    control.resize(620, 65)
    control.show()
    try:
        control.configure('Amazon Polly', 'Justin')
        control.slider.setValue(20)
        assert control.slider.property('pitchRoute') == 'ssml'
        assert 'SSML' in control.value_label.text()
        assert SSML_COLOR in control.slider.styleSheet() and LOCAL_COLOR in control.slider.styleSheet()
        control.slider.setValue(51)
        assert control.slider.property('pitchRoute') == 'local'
        assert 'Local' in control.value_label.text()
        QtTest.QTest.mouseClick(control.reset, QtCore.Qt.LeftButton)
        assert control.slider.value() == 0 and 'Natural' in control.value_label.text()
        QtTest.QTest.keyClick(control.slider, QtCore.Qt.Key_Right)
        assert control.slider.value() == 1  # The detent must not swallow keyboard edits.
        control.slider.setValue(100)
        QtTest.QTest.mouseDClick(control.slider, QtCore.Qt.LeftButton)
        assert control.slider.value() == 0
        control.configure('Amazon Polly', 'Ola [Neural]')
        control.slider.setValue(20)
        assert control.slider.property('pitchRoute') == 'local'
        assert SSML_COLOR not in control.slider.styleSheet()
        assert 'throughout' in control.legend.text()
    finally:
        control.close()


def test_drag_release_near_zero_snaps_before_persistence(gui):
    from vrchat_speech_assistant.pitch_control import PitchSlider
    app, _ = gui
    slider = PitchSlider()
    slider.resize(600, 35)
    slider.show()
    saved = []
    slider.sliderReleased.connect(lambda: saved.append(slider.value()))
    slider.setValue(2)
    app.processEvents()
    option = QtWidgets.QStyleOptionSlider()
    slider.initStyleOption(option)
    handle = slider.style().subControlRect(QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderHandle, slider)
    try:
        QtTest.QTest.mousePress(slider, QtCore.Qt.LeftButton, pos=handle.center())
        assert slider.isSliderDown()
        QtTest.QTest.mouseRelease(slider, QtCore.Qt.LeftButton, pos=handle.center())
        assert slider.value() == 0 and saved == [0]
    finally:
        slider.close()
