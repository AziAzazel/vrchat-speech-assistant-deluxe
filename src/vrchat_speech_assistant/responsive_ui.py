"""Reflow whole control sections into one, two or three columns."""
from PySide6 import QtCore, QtWidgets


class ResponsiveCards(QtWidgets.QWidget):
    def __init__(self, cards, parent=None):
        super().__init__(parent)
        self.cards = cards
        self.columns = 0
        self.grid = QtWidgets.QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.grid.setAlignment(QtCore.Qt.AlignTop)
        self.reflow()

    def reflow(self):
        columns = max(1, min(3, self.width() // 400))
        if columns == self.columns:
            return
        self.columns = columns
        while self.grid.count():
            self.grid.takeAt(0)
        for column in range(3):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns, QtCore.Qt.AlignTop)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()
