"""Context menus and a single-action shortcut editor using the shared registry."""
from PySide6 import QtCore, QtGui, QtWidgets
from vrchat_speech_assistant.shortcut_editor import HotkeySettingsDialog, ShortcutEdit
from vrchat_speech_assistant.shortcut_conflicts import known_conflicts, confirm_conflicts


def attach_shortcut_menu(button, window, action):
    button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    button.setProperty('shortcut_action', action)
    def menu_at(position):
        menu = QtWidgets.QMenu(button)
        assign = menu.addAction('Assign / change shortcut…')
        remove = menu.addAction('Remove shortcut')
        remove.setEnabled(bool(dict(window.configured_hotkeys()).get(action)))
        settings = menu.addAction('Edit language preset…') if action.startswith('language_preset_') else None
        chosen = menu.exec(button.mapToGlobal(position))
        if chosen is assign:
            ButtonShortcutDialog(window, action, button.text()).exec()
        elif chosen is remove:
            window.save_action_shortcut(action, '')
        elif settings is not None and chosen is settings:
            window.edit_roleplay(action)
    button.customContextMenuRequested.connect(menu_at)


class ButtonShortcutDialog(HotkeySettingsDialog):
    def __init__(self, window, action, title):
        super().__init__(window)
        self.window, self.action = window, action
        self.setWindowTitle('Shortcut: ' + title)
        layout = QtWidgets.QVBoxLayout(self)
        self.editor = ShortcutEdit(QtGui.QKeySequence(dict(window.configured_hotkeys()).get(action, '')))
        self.notice = QtWidgets.QLabel()
        self.notice.setWordWrap(True)
        layout.addWidget(QtWidgets.QLabel('Click the field and press a shortcut. Delete / Backspace clears it.'))
        layout.addWidget(self.editor)
        layout.addWidget(self.notice)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.editor.textChanged.connect(self.preview)
        self.preview()
        self.resize(510, 200)

    def preview(self):
        self.notice.setText('\n'.join(known_conflicts(self.editor.text())) or
                            'No known default conflict in the local catalogue. Custom game/OS bindings may differ.')

    def save(self):
        sequence = self.editor.keySequence().toString(QtGui.QKeySequence.PortableText)
        try:
            self.window.validate_action_shortcut(self.action, sequence)
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, 'Invalid shortcut', str(error))
            return
        if not confirm_conflicts(self, [sequence]):
            return
        self.window.save_action_shortcut(self.action, sequence)
        self.accept()
