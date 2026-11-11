"""Editable phrases with explicit language, voice and destination."""
import json
from pathlib import Path
from PySide6 import QtGui, QtWidgets
from vrchat_speech_assistant.languages import DEEPL, VOICES
from vrchat_speech_assistant.roleplay import ACTIONS, DEFAULT_HOTKEYS
from vrchat_speech_assistant.soundboard import OUTPUTS, PROVIDERS, validate_presets
from vrchat_speech_assistant.windows_speech import WindowsSpeech


class SoundboardDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.setWindowTitle('Soundboard phrases and hotkeys')
        self.resize(1120, 460)
        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel(
            'Each shortcut sends exactly the saved phrase, without translation, random endings or personality effects. '
            'Choose a voice that speaks the selected language. Japanese example: ぽい (poi). '
            'Global shortcuts follow the main Global hotkeys setting. Clear a shortcut to disable it. '
            'Polly needs your AWS keys; Windows voices must be installed; Piper uses the configured model for that language.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Shortcut', 'Phrase', 'Language', 'Output', 'Provider', 'Voice'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.table)
        for preset in parent.soundboard_presets:
            self.add_row(preset)
        controls = QtWidgets.QHBoxLayout()
        for title, callback in [('Add phrase', lambda: self.add_row()), ('Remove selected', self.remove_selected),
                                ('Play selected', self.play_selected)]:
            button = QtWidgets.QPushButton(title)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_row(self, preset=None):
        if self.table.rowCount() >= 32:
            return
        preset = preset or {'key': '', 'text': 'Hello', 'language': 'English', 'output': 'Voice only',
                            'provider': 'Windows Speech', 'voice': ''}
        row = self.table.rowCount()
        self.table.insertRow(row)
        key = QtWidgets.QKeySequenceEdit(QtGui.QKeySequence(preset['key']))
        # One chord per phrase; sequences cannot be registered as global hotkeys.
        key.setMaximumSequenceLength(1)
        phrase = QtWidgets.QLineEdit(preset['text'])
        phrase.setMaxLength(2500)
        self.table.setCellWidget(row, 0, key)
        self.table.setCellWidget(row, 1, phrase)
        language, output, provider, voice = [QtWidgets.QComboBox() for _ in range(4)]
        for column, combo, values, selected in [(2, language, DEEPL, preset['language']),
                                               (3, output, OUTPUTS, preset['output']),
                                               (4, provider, PROVIDERS, preset['provider'])]:
            combo.addItems(values)
            combo.setCurrentText(selected)
            self.table.setCellWidget(row, column, combo)
        self.table.setCellWidget(row, 5, voice)
        def refresh():
            selected = voice.currentText() or preset['voice']
            voice.clear()
            voices = []
            if provider.currentText() == 'Amazon Polly':
                voices = VOICES['polly'].get(language.currentText()) or []
            elif provider.currentText() == 'Windows Speech':
                if self.window.windows_speech is None:
                    try:
                        self.window.windows_speech = WindowsSpeech()
                    except Exception:
                        pass
                voices = list(self.window.windows_speech.voices) if self.window.windows_speech else []
            else:
                settings = self.window.config['SPEECH']
                model = settings.get('piper_model_' + language.currentText()) or settings.get('piper_model')
                voices = [Path(model).stem] if model else []
            voice.addItems(voices)
            if selected in voices:
                voice.setCurrentText(selected)
            voice.setEnabled(output.currentText() != 'Chatbox only')
            provider.setEnabled(output.currentText() != 'Chatbox only')
        language.currentTextChanged.connect(refresh)
        provider.currentTextChanged.connect(refresh)
        output.currentTextChanged.connect(refresh)
        refresh()
        self.table.selectRow(row)

    def remove_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def preset(self, row):
        return {'key': self.table.cellWidget(row, 0).keySequence().toString(QtGui.QKeySequence.PortableText),
                'text': self.table.cellWidget(row, 1).text(),
                **{field: self.table.cellWidget(row, column).currentText()
                   for column, field in [(2, 'language'), (3, 'output'), (4, 'provider'), (5, 'voice')]}}

    def play_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            self.window.play_soundboard(self.preset(row))

    def save(self):
        presets = [self.preset(row) for row in range(self.table.rowCount())]
        settings = self.window.config['ROLEPLAY']
        try:
            validate_presets(presets, [settings.get('key_' + action, DEFAULT_HOTKEYS[action]) for action in ACTIONS])
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, 'Invalid soundboard settings', str(error))
            return
        self.window.config['SOUNDBOARD']['presets'] = json.dumps(presets, ensure_ascii=False)
        self.window.save_config()
        self.window.soundboard_presets = presets
        self.window._init_hotkeys()
        self.accept()
