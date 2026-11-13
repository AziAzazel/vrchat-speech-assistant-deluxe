"""Shared final chatbox formatting and a paged, read-only preview."""
from PySide6 import QtWidgets
from chatbox_osc.main import text_with_font
from vrchat_speech_assistant.live_chatbox import split_pages, utf16_units, MAX_UNITS
from vrchat_speech_assistant.roleplay import PERSONALITIES
from vrchat_speech_assistant.text_tools import decorate_chatbox


def format_chatbox(result, source, font, rules, roleplay, override=None):
    if override is not None:
        text = override
    else:
        text = decorate_chatbox(result, rules, source)
        if roleplay.get('chatbox_tag', 'false').lower() == 'true':
            tag = PERSONALITIES.get(roleplay.get('personality'), PERSONALITIES['Neutral'])[1]
            if tag:
                text = tag + ' ' + text
    return text_with_font(text, font)


class ChatboxPreview(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pages, self.index = [], 0
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.note = QtWidgets.QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.text = QtWidgets.QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumHeight(90)
        self.text.setMinimumHeight(65)
        layout.addWidget(self.text)
        row = QtWidgets.QHBoxLayout()
        self.previous = QtWidgets.QPushButton('←')
        self.next = QtWidgets.QPushButton('→')
        self.counter = QtWidgets.QLabel()
        self.previous.clicked.connect(lambda: self.show_page(self.index - 1))
        self.next.clicked.connect(lambda: self.show_page(self.index + 1))
        row.addWidget(self.previous)
        row.addWidget(self.counter, 1)
        row.addWidget(self.next)
        layout.addLayout(row)
        self.set_text('')

    def set_text(self, text, final=False):
        self.pages = split_pages(text)
        self.note.setText('Final chatbox pages for this output.' if final else
                          'Draft chatbox pages. Translation/random endings can change the final pages; preview does not send text.')
        self.show_page(0)

    def show_page(self, index):
        self.index = max(0, min(index, len(self.pages) - 1))
        text = self.pages[self.index] if self.pages else ''
        self.text.setPlainText(text)
        self.counter.setText(f'Page {self.index + 1 if self.pages else 0} / {len(self.pages)} · VRChat limit: {utf16_units(text)} / {MAX_UNITS}')
        self.previous.setEnabled(self.index > 0)
        self.next.setEnabled(self.index + 1 < len(self.pages))
