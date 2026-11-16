from vrchat_speech_assistant.shortcut_conflicts import known_conflicts
from vrchat_speech_assistant.hotkeys import parse_hotkey


def test_catalogue_canonicalizes_modifiers_and_recognizes_system_and_game_defaults():
    assert 'Task Manager' in '\n'.join(known_conflicts('Shift+Ctrl+Esc'))
    assert 'nameplates' in '\n'.join(known_conflicts('Ctrl+N'))
    assert 'hand gesture' in '\n'.join(known_conflicts('Shift+F3'))
    assert known_conflicts('Win+L') == known_conflicts('Meta+L')
    assert not known_conflicts('Ctrl+Alt+Shift+F20')
    assert not known_conflicts('')
    assert not known_conflicts('Invalid')
    assert parse_hotkey('Alt+Tab') == (1, 9)
