from copy import deepcopy
import pytest
from vrchat_speech_assistant.hotkeys import parse_hotkey
from vrchat_speech_assistant.soundboard import DEFAULT_PRESETS, validate_presets


def test_semicolon_hotkey_and_conflicts():
    assert parse_hotkey('Ctrl+;') == (2, 0xBA)
    assert parse_hotkey('Ctrl+Shift+;') == (6, 0xBA)
    with pytest.raises(ValueError):
        validate_presets(DEFAULT_PRESETS, ['Ctrl+;'])
    with pytest.raises(ValueError):
        validate_presets(DEFAULT_PRESETS * 2)


@pytest.mark.parametrize('field,value', [('language', 'Unknown'), ('output', 'Unknown'), ('text', ''), ('text', 'x'*2501), ('provider', 'Unknown')])
def test_invalid_presets_rejected(field, value):
    preset = dict(DEFAULT_PRESETS[0], **{field: value})
    with pytest.raises(ValueError):
        validate_presets([preset])


def test_disabled_hotkeys_and_empty_soundboard_are_valid():
    assert validate_presets([]) == []
    preset = dict(DEFAULT_PRESETS[0], key='')
    assert validate_presets([preset, deepcopy(preset)])


def test_separate_caption_and_standard_polly_whisper_are_valid():
    preset = dict(DEFAULT_PRESETS[0], output='Voice + chatbox', chatbox_text='👀', delivery='Whispered')
    assert validate_presets([preset]) == [preset]


@pytest.mark.parametrize('extra', [
    {'chatbox_text': None}, {'chatbox_text': 'x'*2501}, {'delivery': 'Unknown'},
    {'delivery': 'Whispered', 'provider': 'Windows Speech'},
    {'delivery': 'Whispered', 'provider': 'Piper (offline)'},
    {'delivery': 'Whispered', 'voice': 'Kazuha [Neural]'},
    {'pitch': -51}, {'pitch': 51}, {'pitch': True}, {'pitch': 1.5}, {'pitch': '20'},
    {'pitch': None}, {'pitch': 10, 'provider': 'Windows Speech'},
    {'pitch': -10, 'provider': 'Piper (offline)'},
    {'pitch': 10, 'voice': 'Kazuha [Neural]'},
    {'favorite': 'yes'},
])
def test_invalid_caption_or_unsupported_whisper_rejected(extra):
    with pytest.raises(ValueError):
        validate_presets([dict(DEFAULT_PRESETS[0], **extra)])
