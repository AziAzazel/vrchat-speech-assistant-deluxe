"""Large buttons backed by saved Soundboard entries."""
from PySide6 import QtWidgets

STARTERS = {
    'Polish': ('Tak', 'Nie', 'Chodź', 'Poczekaj', 'Nie rozumiem', 'Powtórz'),
    'English': ('Yes', 'No', 'Come here', 'Wait', "I don't understand", 'Please repeat'),
}


class FavoriteReactions(QtWidgets.QWidget):
    def __init__(self, play, edit, parent=None):
        super().__init__(parent)
        self.play = play
        self.buttons = []
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        note = QtWidgets.QLabel('One click plays the saved Soundboard voice/output. Mark Favorite in Soundboard settings to choose buttons.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.grid = QtWidgets.QGridLayout()
        layout.addLayout(self.grid)
        self.empty = QtWidgets.QLabel('No favorite reactions yet.')
        layout.addWidget(self.empty)
        button = QtWidgets.QPushButton('Edit favorites / Soundboard…')
        button.clicked.connect(edit)
        layout.addWidget(button)

    def refresh(self, presets, busy=False):
        for button in self.buttons:
            self.grid.removeWidget(button)
            button.deleteLater()
        self.buttons = []
        for preset in presets:
            if not preset.get('favorite', False):
                continue
            text = preset['text']
            button = QtWidgets.QPushButton(text if len(text) <= 28 else text[:27] + '…')
            button.setMinimumHeight(64)
            font = button.font()
            font.setPointSize(13)
            font.setBold(True)
            button.setFont(font)
            button.setToolTip(f"{text}\n{preset['language']} · {preset['voice']} · {preset['output']}")
            button.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, saved=dict(preset): self.play(saved))
            self.buttons.append(button)
        self.empty.setVisible(not self.buttons)
        self.reflow()
        self.set_busy(busy)

    def set_busy(self, busy):
        for button in self.buttons:
            button.setEnabled(not busy)

    def reflow(self):
        columns = max(1, min(3, self.width() // 170))
        while self.grid.count():
            self.grid.takeAt(0)
        for column in range(3):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        for index, button in enumerate(self.buttons):
            self.grid.addWidget(button, index // columns, index % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()
