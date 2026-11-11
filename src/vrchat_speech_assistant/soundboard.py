"""Saved phrases have explicit routes and never depend on translation."""
from vrchat_speech_assistant.hotkeys import parse_hotkey
from vrchat_speech_assistant.languages import DEEPL

OUTPUTS = ('Voice only', 'Chatbox only', 'Voice + chatbox')
PROVIDERS = ('Amazon Polly', 'Windows Speech', 'Piper (offline)')
DEFAULT_PRESETS = [{'key': 'Ctrl+;', 'text': 'ぽい', 'language': 'Japanese',
                    'output': 'Voice only', 'provider': 'Amazon Polly', 'voice': 'Mizuki'}]


def validate_presets(presets, other_keys=()):
    if not isinstance(presets, list) or len(presets) > 32:
        raise ValueError('Use at most 32 soundboard phrases.')
    seen = {parse_hotkey(key) for key in other_keys if key}
    for preset in presets:
        if not isinstance(preset, dict) or any(not isinstance(preset.get(field), str) for field in DEFAULT_PRESETS[0]):
            raise ValueError('Invalid soundboard phrase.')
        if not preset['text'].strip() or len(preset['text']) > 2500:
            raise ValueError('Each phrase needs 1–2500 characters.')
        if preset['language'] not in DEEPL or preset['output'] not in OUTPUTS or preset['provider'] not in PROVIDERS:
            raise ValueError('Choose a supported language, output and provider.')
        if preset['key']:
            canonical = parse_hotkey(preset['key'])
            if canonical in seen:
                raise ValueError('Soundboard and Roleplay shortcuts must be different.')
            seen.add(canonical)
        if preset['output'] != 'Chatbox only' and not preset['voice'].strip():
            raise ValueError('Choose a voice for every spoken phrase.')
    return presets


class LazySpeech:
    """Create the selected backend inside the cancellable output worker."""
    def __init__(self, factory):
        self.factory = factory

    def speech(self, *args):
        from vrchat_speech_assistant.output_control import check_cancelled
        check_cancelled()
        backend = self.factory()
        check_cancelled()
        return backend.speech(*args)
