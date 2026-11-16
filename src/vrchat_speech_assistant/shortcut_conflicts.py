"""Small offline advisory catalogue; user/game remaps cannot be detected.

References: https://support.microsoft.com/windows/keyboard-shortcuts-in-windows
https://docs.vrchat.com/docs/keyboard-and-mouse
Only selected common desktop defaults are covered, not an exhaustive OS registry.
"""
from PySide6 import QtWidgets
from vrchat_speech_assistant.hotkeys import parse_hotkey

WINDOWS = {
    'Alt+Tab': 'switch applications', 'Alt+F4': 'close window',
    'Alt+Space': 'window menu', 'Alt+Return': 'fullscreen in many applications',
    'Tab': 'next control', 'Shift+Tab': 'previous control',
    'Ctrl+Tab': 'next tab', 'Esc': 'cancel / close menu', 'Ctrl+Shift+Esc': 'Task Manager',
    'Ctrl+Esc': 'Start menu', 'Ctrl+Alt+Delete': 'Windows security screen',
    'Meta+L': 'lock Windows', 'Meta+D': 'show desktop', 'Meta+E': 'File Explorer',
    'Meta+R': 'Run', 'Meta+I': 'Settings', 'Meta+Tab': 'Task View',
    'Meta+Space': 'input language', 'Meta+Shift+S': 'screen capture',
    'Meta+V': 'clipboard history', 'Meta+G': 'Game Bar',
    **{f'Ctrl+{key}': name for key, name in [('C','copy'), ('V','paste'), ('X','cut'),
        ('Z','undo'), ('Y','redo'), ('A','select all'), ('S','save'), ('F','find')]},
    'F12': 'reserved debugger key / commonly Steam screenshot',
}
VRCHAT = {
    'Esc': 'Quick Menu', 'Space': 'jump',
    'Ctrl+N': 'toggle nameplates', 'Ctrl+H': 'toggle HUD',
    'Ctrl+\\': 'reset avatar',
    **{f'Shift+F{i}': 'desktop hand gesture' for i in range(1, 9)},
}


def known_conflicts(sequence):
    if not sequence:
        return []
    try:
        key = parse_hotkey(sequence)
    except ValueError:
        return []
    warnings = []
    for source, catalogue in (('Windows / common apps', WINDOWS), ('VRChat desktop', VRCHAT)):
        for binding, meaning in catalogue.items():
            if key == parse_hotkey(binding):
                warnings.append(f'{source}: {binding} — {meaning}')
    if key[0] & 8 and not any('Windows' in warning for warning in warnings):
        warnings.append('Windows: Win/Meta combinations may be reserved by the system.')
    return warnings


def confirm_conflicts(parent, sequences):
    messages = list(dict.fromkeys(message for key in sequences for message in known_conflicts(key)))
    if not messages:
        return True
    text = '\n'.join(messages) + '\n\nThis may trigger or block a system/game action, or fail to register. Defaults vary with remaps and keyboard layout; this list is not exhaustive. Save anyway?'
    return QtWidgets.QMessageBox.warning(parent, 'Possible shortcut conflicts', text,
        QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Cancel,
        QtWidgets.QMessageBox.Cancel) == QtWidgets.QMessageBox.Save
