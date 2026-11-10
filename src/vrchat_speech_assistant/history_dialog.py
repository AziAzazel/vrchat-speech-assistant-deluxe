"""Session-only bounded utterance history; no transcript files or log output."""
from PySide6 import QtCore, QtWidgets


class HistoryDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.setWindowTitle("Session history (memory only)")
        self.resize(850, 550)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel("Last 50 attempts, including stopped/failed output. Replay uses the current voice and pronunciation, without translating or adding another random ending.")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "Status", "Language", "Result / original text"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
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
        clear = QtWidgets.QPushButton("Clear history")
        clear.clicked.connect(parent.clear_history)
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.reject)
        for button in (self.load_button, self.replay_button, clear, close):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.refresh()

    def selected(self):
        item = self.table.item(self.table.currentRow(), 0)
        return item.data(QtCore.Qt.UserRole) if item else None

    def refresh(self):
        selected = self.selected()
        self.table.setRowCount(0)
        row_to_select = 0
        for entry in reversed(self.window.history):
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [entry["time"], entry["status"], entry["language"], entry["result"] or entry["source"]]
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                self.table.setItem(row, column, item)
                if column == 0:
                    item.setData(QtCore.Qt.UserRole, entry)
            if selected and entry["id"] == selected["id"]:
                row_to_select = row
        if self.table.rowCount():
            self.table.selectRow(row_to_select)
        self.show_details()

    def show_details(self):
        entry = self.selected()
        self.load_button.setEnabled(bool(entry))
        self.replay_button.setEnabled(bool(entry and entry["result"]))
        self.details.setPlainText("" if not entry else
            f"Original: {entry['source']}\n\nResult / chatbox base: {entry['result']}\n\nSpoken pronunciation: {entry['spoken']}\n\nProvider: {entry['provider']} | Voice: {entry['voice']}")

    def load(self):
        entry = self.selected()
        if entry and self.window.load_history_source(entry):
            self.accept()

    def replay(self):
        entry = self.selected()
        if entry and self.window.replay_history(entry):
            self.accept()
