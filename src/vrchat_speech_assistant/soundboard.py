"""Saved phrases have explicit routes and never depend on translation."""
from pathlib import Path
from vrchat_speech_assistant.hotkeys import parse_hotkey
from vrchat_speech_assistant.languages import DEEPL

OUTPUTS = ('Voice only', 'Chatbox only', 'Voice + chatbox')
PROVIDERS = ('Amazon Polly', 'Windows Speech', 'Piper (offline)')
DELIVERIES = ('Normal', 'Whispered')
DEFAULT_PRESETS = [{'key': 'Ctrl+;', 'text': 'ぽい', 'language': 'Japanese',
                    'output': 'Voice only', 'provider': 'Amazon Polly', 'voice': 'Mizuki'}]


def phrase_tags(preset):
    tags = {'whispered': True} if preset.get('delivery') == 'Whispered' else {}
    if preset.get('pitch', 0):
        tags['pitch'] = preset['pitch']
    return tags


def validate_presets(presets, other_keys=()):
    if not isinstance(presets, list) or len(presets) > 32:
        raise ValueError('Use at most 32 soundboard phrases.')
    seen = {parse_hotkey(key) for key in other_keys if key}
    for preset in presets:
        if not isinstance(preset, dict) or any(not isinstance(preset.get(field), str) for field in DEFAULT_PRESETS[0]):
            raise ValueError('Invalid soundboard phrase.')
        if not preset['text'].strip() or len(preset['text']) > 2500:
            raise ValueError('Each phrase needs 1–2500 characters.')
        recording = preset.get('kind', 'phrase') == 'audio'
        if preset.get('kind', 'phrase') not in ('phrase', 'audio'):
            raise ValueError('Unknown soundboard entry type.')
        if not recording:
            chatbox = preset.get('chatbox_text', '')
            if not isinstance(chatbox, str) or len(chatbox) > 2500:
                raise ValueError('Chatbox text must contain at most 2500 characters.')
            delivery = preset.get('delivery', 'Normal')
            if delivery not in DELIVERIES:
                raise ValueError('Choose a supported phrase delivery.')
            pitch = preset.get('pitch', 0)
            if type(pitch) is not int or not -50 <= pitch <= 50:
                raise ValueError('Phrase pitch must be a whole number between -50 and +50%.')
            if (delivery == 'Whispered' or pitch) and preset['output'] != 'Chatbox only':
                if preset['provider'] != 'Amazon Polly':
                    raise ValueError('Whisper and pitch require an Amazon Polly Standard voice, such as Mizuki. Use Normal delivery and pitch 0 for local voices.')
                from vrchat_speech_assistant.providers import validate_polly_style
                validate_polly_style(preset['voice'], phrase_tags(preset))
        if recording:
            if not isinstance(preset.get('audio'), str) or Path(preset['audio']).suffix.lower() not in ('.wav', '.mp3'):
                raise ValueError('Select a WAV or MP3 recording.')
            if not isinstance(preset.get('subtitle', ''), str) or (preset.get('subtitle') and Path(preset['subtitle']).suffix.lower() != '.srt'):
                raise ValueError('Select an SRT subtitle file, or leave it empty.')
            if type(preset.get('offset_ms', 0)) is not int or not -10000 <= preset.get('offset_ms', 0) <= 10000:
                raise ValueError('Subtitle offset must be between -10000 and 10000 ms.')
            if preset['output'] == 'Chatbox only' and not preset.get('subtitle'):
                raise ValueError('Subtitle-only playback requires an SRT file.')
        if preset['language'] not in DEEPL or preset['output'] not in OUTPUTS or (not recording and preset['provider'] not in PROVIDERS):
            raise ValueError('Choose a supported language, output and provider.')
        if preset['key']:
            canonical = parse_hotkey(preset['key'])
            if canonical in seen:
                raise ValueError('Soundboard and Roleplay shortcuts must be different.')
            seen.add(canonical)
        if not recording and preset['output'] != 'Chatbox only' and not preset['voice'].strip():
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
