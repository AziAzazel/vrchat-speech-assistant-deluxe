"""Session-only bounded utterance history; no transcript files or log output."""
from PySide6 import QtCore, QtWidgets
from vrchat_speech_assistant.audio_export import save_generated_audio
from vrchat_speech_assistant.diagnostics import record_failure
import sys


class HistoryDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.setWindowTitle("Session history (memory only)")
        self.resize(850, 550)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel("Last 50 attempts, including stopped/failed output. Replay uses current settings. Only the latest generated speech audio is retained for export (up to 32 MB); select its Available row. Saving does not synthesize again.")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Time", "Status", "Language", "Result / original text", "Audio"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self.show_details)
        layout.addWidget(self.table)
        self.details = QtWidgets.QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(170)
        layout.addWidget(self.details)
        buttons = QtWidgets.QHBoxLayout()
        self.load_button = QtWidgets.QPushButton("Load original into editor")
        self.load_button.clicked.connect(self.load)
        self.replay_button = QtWidgets.QPushButton("Repeat result")
        self.replay_button.clicked.connect(self.replay)
        self.save_audio_button = QtWidgets.QPushButton('Save speech audio…')
        self.save_audio_button.setToolTip('Save the original generated WAV/OGG for the selected Available row, without another cloud request.')
        self.save_audio_button.clicked.connect(self.export_audio)
        clear = QtWidgets.QPushButton("Clear history")
        clear.clicked.connect(parent.clear_history)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.reject)
        for button in (self.load_button, self.replay_button, self.save_audio_button, clear, close):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.refresh()

    def selected(self):
        item = self.table.item(self.table.currentRow(), 0)
        identifier = item.data(QtCore.Qt.UserRole) if item else None
        return next((entry for entry in self.window.history if entry['id'] == identifier), None)

    def refresh(self):
        selected = self.selected()
        self.table.setRowCount(0)
        row_to_select = 0
        for entry in reversed(self.window.history):
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [entry["time"], entry["status"], entry["language"], entry["result"] or entry["source"],
                      'Available' if entry.get('audio') is not None else '—']
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                self.table.setItem(row, column, item)
                if column == 0:
                    # Keep only IDs in Qt; closed dialogs must not retain old audio buffers.
                    item.setData(QtCore.Qt.UserRole, entry['id'])
            if selected and entry["id"] == selected["id"]:
                row_to_select = row
        if self.table.rowCount():
            self.table.selectRow(row_to_select)
        self.show_details()

    def show_details(self):
        entry = self.selected()
        self.load_button.setEnabled(bool(entry))
        self.replay_button.setEnabled(bool(entry and entry["result"]))
        self.save_audio_button.setEnabled(bool(entry and entry.get('audio') is not None))
        self.details.setPlainText("" if not entry else
            f"Original: {entry['source']}\n\nResult / chatbox base: {entry['result']}\n\nSpoken pronunciation: {entry['spoken']}\n\nSeparate chatbox text: {entry.get('chatbox_override', 'Same as result')}\n\nProvider: {entry['provider']} | Voice: {entry['voice']}\n\nAudio: {entry['audio'].extension if entry.get('audio') is not None else entry.get('audio_note', 'No retained audio for this row')}")

    def export_audio(self):
        entry = self.selected()
        clip = entry.get('audio') if entry else None
        if clip is None:
            return
        dialog = QtWidgets.QFileDialog(self, 'Save generated speech audio')
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dialog.setDefaultSuffix(clip.extension[1:])
        dialog.setNameFilter('WAV audio (*.wav)' if clip.extension == '.wav' else 'Ogg Vorbis audio (*.ogg)')
        dialog.selectFile(f"Speech-{entry['id']}{clip.extension}")
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            save_generated_audio(clip, dialog.selectedFiles()[0])
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, 'Audio format', str(error))
        except OSError:
            record_failure('Save generated speech audio', *sys.exc_info()[::2])
            QtWidgets.QMessageBox.warning(self, 'Could not save audio', 'Choose a writable location. See diagnostic logs.')
        else:
            self.window.log_info('Speech audio saved without another synthesis request.')

    def load(self):
        entry = self.selected()
        if entry and self.window.load_history_source(entry):
            self.accept()

    def replay(self):
        entry = self.selected()
        if entry and self.window.replay_history(entry):
            self.accept()
