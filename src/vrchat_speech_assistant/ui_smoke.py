"""Checks shared by the frozen Windows and Linux application smoke tests."""
def verify_local_pitch(directory):
    """Exercise the bundled decoder, DSP and final-audio export without AWS."""
    import io
    from pathlib import Path
    import numpy as np
    import soundfile as sf
    from vrchat_speech_assistant.audio_effects import pitched_audio
    from vrchat_speech_assistant.audio_export import read_generated_audio, save_generated_audio
    from vrchat_speech_assistant.providers import validate_polly_style
    rate = 22050
    samples = .25 * np.sin(2 * np.pi * 440 * np.arange(rate * 2) / rate)
    source = Path(directory) / 'pitch-source.ogg'
    sf.write(str(source), samples, rate, format='OGG', subtype='VORBIS')
    for pitch in (-75, 100, 300):
        validate_polly_style('Ola [Neural]', {'pitch': pitch})
        with pitched_audio(source, {'pitch': pitch}) as processed:
            clip = read_generated_audio(processed)
            export = Path(directory) / 'pitch-export.wav'
            save_generated_audio(clip, export)
            assert export.read_bytes() == processed.read_bytes()
        audio, actual_rate = sf.read(io.BytesIO(clip.data))
        assert len(audio) == len(samples) and actual_rate == rate
        middle = audio[rate//2:3*rate//2]
        frequency = np.argmax(abs(np.fft.rfft(middle * np.hanning(len(middle)))))
        assert abs(frequency - 440 * (1 + pitch/100)) < 3


def verify_workspace(window, app):
    from vrchat_speech_assistant.shortcut_conflicts import known_conflicts
    assert window.tabs.count() == 6
    for width in (650, 1100, 1500, 650):
        window.resize(width, 800)
        app.processEvents()
        assert window.transport.columns == (4 if width >= 820 else 2)
        assert window.transport.geometry().bottom() < window.tabs.geometry().top()
        assert window.status_bar.geometry().top() > window.tabs.geometry().bottom()
    draft = window.manual_text.toPlainText()
    window.transport.compact.setChecked(True)
    app.processEvents()
    assert window.tabs.tabBar().isHidden()
    assert window.stop_speech_button.isVisible() and window.speak_button.isVisible()
    assert window.manual_text.toPlainText() == draft
    window.show_workspace_tab('History')
    assert not window.transport.compact.isChecked()
    assert window.history_view.isVisible()
    assert window.history_view.table.rowCount() == len(window.history)
    window.show_workspace_tab('Soundboard')
    assert window.soundboard_library.table.rowCount() == len(window.soundboard_presets)
    window.show_workspace_tab('Conversation')
    assert window.stop_speech_button.property('shortcut_action') == 'stop_speaking'
    assert len(window.language_preset_buttons) == 4
    assert known_conflicts('Ctrl+N') and known_conflicts('Alt+F4')
