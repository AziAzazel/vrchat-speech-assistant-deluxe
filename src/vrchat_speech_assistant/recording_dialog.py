"""Local audio and optional subtitle file selection."""
from pathlib import Path
from PySide6 import QtWidgets, QtGui
from vrchat_speech_assistant.shortcut_editor import HotkeySettingsDialog, ShortcutEdit
from vrchat_speech_assistant.soundboard import OUTPUTS, validate_presets


class RecordingDialog(HotkeySettingsDialog):
    def __init__(self, parent, preset=None):
        super().__init__(parent.window)
        self.setWindowTitle('Recording and SRT subtitles')
        self.resize(680, 320)
        self.result_preset = None
        self.original = preset or {'kind': 'audio', 'text': 'Recording', 'language': 'English',
                                   'provider': 'Audio file', 'voice': 'Recording', 'key': '',
                                   'output': 'Voice only', 'audio': '', 'subtitle': '', 'offset_ms': 0}
        layout = QtWidgets.QFormLayout(self)
        self.key = ShortcutEdit(QtGui.QKeySequence(self.original['key']))
        layout.addRow('Shortcut:', self.key)
        self.audio = QtWidgets.QLineEdit(self.original.get('audio', ''))
        self.subtitle = QtWidgets.QLineEdit(self.original.get('subtitle', ''))
        for title, edit, callback in [('WAV / MP3:', self.audio, self.choose_audio), ('SRT (optional):', self.subtitle, self.choose_subtitle)]:
            row = QtWidgets.QHBoxLayout()
            row.addWidget(edit)
            button = QtWidgets.QPushButton('Browse…')
            button.clicked.connect(callback)
            row.addWidget(button)
            layout.addRow(title, row)
        self.offset = QtWidgets.QSpinBox()
        self.offset.setRange(-10000, 10000)
        self.offset.setSuffix(' ms')
        self.offset.setValue(self.original.get('offset_ms', 0))
        layout.addRow('Subtitle offset (+ delays, − advances):', self.offset)
        self.output = QtWidgets.QComboBox()
        self.output.addItems(OUTPUTS)
        self.output.setCurrentText(self.original['output'])
        layout.addRow('Output (voice = recording):', self.output)
        note = QtWidgets.QLabel('Files stay on your computer; their paths are saved. SRT uses timed lines, not word-by-word karaoke. '
                                'Chatbox updates are limited to one per 1.5 seconds and 144 characters; faster cues may be skipped. '
                                'Stop stops audio and future subtitles. Positive offset delays subtitles.')
        note.setWordWrap(True)
        layout.addRow(note)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def choose_audio(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose recording', self.audio.text(), 'Audio (*.wav *.mp3)')
        if path:
            self.audio.setText(path)
            sidecar = Path(path).with_suffix('.srt')
            if not self.subtitle.text() and sidecar.is_file():
                self.subtitle.setText(str(sidecar))
                self.output.setCurrentText('Voice + chatbox')

    def choose_subtitle(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose subtitles', self.subtitle.text(), 'Subtitles (*.srt)')
        if path:
            self.subtitle.setText(path)
            self.output.setCurrentText('Voice + chatbox')

    def save(self):
        preset = dict(self.original, kind='audio', audio=self.audio.text().strip(), subtitle=self.subtitle.text().strip(),
                      offset_ms=self.offset.value(), output=self.output.currentText(),
                      key=self.key.keySequence().toString(QtGui.QKeySequence.PortableText))
        title = self.original['text'] if preset['audio'] == self.original.get('audio') else Path(preset['audio']).stem
        preset.update(text=title or 'Recording', voice=Path(preset['audio']).name or 'Recording', provider='Audio file')
        try:
            validate_presets([preset])
            if not Path(preset['audio']).is_file():
                raise ValueError('Choose an existing WAV or MP3 file.')
            if preset['subtitle']:
                from vrchat_speech_assistant.media_playback import load_srt
                load_srt(preset['subtitle'])
        except (ValueError, OSError, UnicodeError) as error:
            QtWidgets.QMessageBox.warning(self, 'Recording settings', 'Could not read the recording or SRT. Check the selected files and timestamps.'
                                         if not isinstance(error, ValueError) else str(error))
            return
        self.result_preset = preset
        self.accept()
