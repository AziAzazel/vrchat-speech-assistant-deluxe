import io
import logging
from unittest.mock import Mock
import pytest

from vrchat_speech_assistant.languages import GOOGLE, DEEPL, VOICES, POLLY_VOICES_ENGINE
from vrchat_speech_assistant.providers import Polly, polly_engine, validate_polly_style, UnsupportedSpeechStyle
from vrchat_speech_assistant.translation import translate_message
from vrchat_speech_assistant.timings import stage_timer


def test_expanded_catalogue_preserves_legacy_voice_labels():
    assert len(GOOGLE) == 86 and len(DEEPL) == 111
    assert VOICES['polly']['Polish'][:4] == ['Ewa', 'Maja', 'Jacek', 'Jan']
    assert 'Ola [Neural]' in VOICES['polly']['Polish']
    assert 'Justin' in VOICES['polly']['English']
    assert polly_engine('Matthew') == 'standard'  # Keep existing whisper/pitch/cache behavior.
    for voices in VOICES['polly'].values():
        for voice in voices or []:
            assert voice.split()[0] in POLLY_VOICES_ENGINE


def test_new_neural_voice_uses_engine_and_supported_ssml(gui, monkeypatch, tmp_path):
    from vrchat_speech_assistant import providers
    monkeypatch.setattr(providers, 'VOICES_PATH', tmp_path)
    monkeypatch.setattr(providers, 'read_ogg_file', Mock())
    polly = Polly.__new__(Polly)
    polly.client = Mock()
    polly.client.synthesize_speech.return_value = {'AudioStream': io.BytesIO(b'audio')}
    polly.speech('Cześć <AI> & przyjaciele', 'Ola [Neural]', 'Cable', {'rate': 85})
    request = polly.client.synthesize_speech.call_args.kwargs
    assert request['Engine'] == 'neural' and request['VoiceId'] == 'Ola'
    assert 'amazon:auto-breaths' not in request['Text']
    assert '<prosody rate="85%">' in request['Text']
    assert '&lt;AI&gt; &amp;' in request['Text']


@pytest.mark.parametrize('tags', [{'whispered': True}, {'pitch': -10}])
def test_neural_unsupported_effect_rejected_before_aws_call(tags):
    polly = Polly.__new__(Polly)
    polly.client = Mock()
    with pytest.raises(UnsupportedSpeechStyle):
        polly.speech('Private sentence', 'Ola [Neural]', 'Cable', tags)
    polly.client.synthesize_speech.assert_not_called()
    validate_polly_style('Ewa', tags)


def test_standard_voice_keeps_whisper_pitch_and_explicit_engine(gui, monkeypatch, tmp_path):
    from vrchat_speech_assistant import providers
    monkeypatch.setattr(providers, 'VOICES_PATH', tmp_path)
    monkeypatch.setattr(providers, 'read_ogg_file', Mock())
    polly = Polly.__new__(Polly)
    polly.client = Mock()
    polly.client.synthesize_speech.return_value = {'AudioStream': io.BytesIO(b'audio')}
    polly.speech('Hello', 'Justin', 'Cable', {'whispered': True, 'pitch': -10})
    request = polly.client.synthesize_speech.call_args.kwargs
    assert request['Engine'] == 'standard'
    assert 'name="whispered"' in request['Text'] and 'pitch="-10%"' in request['Text']


def test_beta_translation_options_do_not_change_english_polish():
    translator = Mock()
    translator.translate_text.return_value.text = 'result'
    options = {'split_sentences': '1', 'formality': 'Informal'}
    translate_message(translator, 'Hello', 'English', 'Polish', options)
    request = translator.translate_text.call_args.kwargs
    assert request['source_lang'] == 'EN' and request['target_lang'] == 'PL'
    assert 'model_type' not in request and 'extra_body_parameters' not in request
    translate_message(translator, 'Hello', 'English', 'Welsh', options)
    request = translator.translate_text.call_args.kwargs
    assert request['extra_body_parameters'] == {'enable_beta_languages': True}
    assert request['model_type'] == 'quality_optimized'


def test_stage_timing_reports_duration_without_content(caplog):
    logger = logging.getLogger('deluxe.timings')
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger='deluxe.timings'):
            with stage_timer('translation'):
                private_text = 'PRIVATE_TRANSCRIPT'
        messages = [record.getMessage() for record in caplog.records if record.name == 'deluxe.timings']
        assert any('duration_seconds=' in message for message in messages)
        assert all(private_text not in message for message in messages)
    finally:
        logger.removeHandler(caplog.handler)
