"""One pitch route for synthesis, cache identity and capability indicators."""
from vrchat_speech_assistant.audio_effects import validate_pitch
from vrchat_speech_assistant.languages import POLLY_VOICES_ENGINE

SSML_MIN_PITCH, SSML_MAX_PITCH = -50, 50


def ssml_pitch_available(provider, voice):
    return provider == 'Amazon Polly' and POLLY_VOICES_ENGINE.get(voice.split(' ', 1)[0], 'standard') == 'standard'


def pitch_route(provider, voice, percent):
    validate_pitch(percent)
    if not percent:
        return 'off'
    if ssml_pitch_available(provider, voice) and SSML_MIN_PITCH <= percent <= SSML_MAX_PITCH:
        return 'ssml'
    return 'local'
