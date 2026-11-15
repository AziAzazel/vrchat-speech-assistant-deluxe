"""Persistent activity and dismissible warning/error notices."""
from PySide6 import QtCore, QtWidgets


class StatusBar(QtWidgets.QFrame):
    def __init__(self, message_label, progressbar, parent=None):
        super().__init__(parent)
        self.setObjectName('statusBar')
        self.setStyleSheet('QFrame#statusBar { border-top: 1px solid #666; }')
        self.issues = {}
        self.state_label = QtWidgets.QLabel('Idle | Listener off')
        self.message_label = message_label
        self.issue_label = QtWidgets.QLabel()
        self.dismiss_button = QtWidgets.QPushButton('Dismiss notices')
        self.dismiss_button.clicked.connect(self.dismiss_issues)
        self.dismiss_button.setToolTip('Dismiss the displayed notices. This does not repair their cause.')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(3)
        layout.addWidget(self.state_label)
        layout.addWidget(message_label)
        notices = QtWidgets.QHBoxLayout()
        notices.addWidget(self.issue_label, 1)
        notices.addWidget(self.dismiss_button)
        layout.addLayout(notices)
        layout.addWidget(progressbar)
        for label in (self.state_label, message_label, self.issue_label):
            label.setTextFormat(QtCore.Qt.PlainText)
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
            label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        # Keep the footer compact even for long provider/device errors; hover
        # over a notice to read its full text.
        message_label.setMaximumHeight(message_label.fontMetrics().lineSpacing() * 2 + 4)
        self.issue_label.setMaximumHeight(self.issue_label.fontMetrics().lineSpacing() * 3 + 4)
        message_label.hide()
        self._refresh_issues()

    def show_message(self, level, text):
        self.message_label.setText(text)
        self.message_label.setToolTip(text)
        self.message_label.setVisible(level == 'info' and bool(text))
        if level in ('warning', 'error'):
            self.issues[level] = text
            self._refresh_issues()

    def dismiss_issues(self):
        self.issues.clear()
        self._refresh_issues()

    def _refresh_issues(self):
        level = 'error' if 'error' in self.issues else 'warning'
        text = self.issues.get(level)
        self.issue_label.setText(f'{level.title()}: {text}' if text else 'No pending notices.')
        self.issue_label.setStyleSheet('color: #ff8080' if level == 'error' else 'color: orange' if text else '')
        self.issue_label.setToolTip('\n'.join(f'{kind.title()}: {value}' for kind, value in self.issues.items()))
        self.dismiss_button.setText(f'Dismiss notices ({len(self.issues)})')
        self.dismiss_button.setVisible(bool(self.issues))
