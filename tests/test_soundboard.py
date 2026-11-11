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
