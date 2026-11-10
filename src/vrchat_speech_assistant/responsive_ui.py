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


class CollapsibleCard(QtWidgets.QFrame):
    collapsedChanged = QtCore.Signal(bool)

    def __init__(self, title, collapsed=False, parent=None):
        super().__init__(parent)
        self.setObjectName("categoryCard")
        self.setStyleSheet("QFrame#categoryCard { background: rgba(66,66,66,128); border: 1px solid #252525; border-radius: 4px; }")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 10)
        self.header = QtWidgets.QToolButton()
        self.header.setText(title)
        self.header.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.header.setCheckable(True)
        self.header.setAutoRaise(True)
        self.header.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.body = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.body)
        self.content_layout.setContentsMargins(0, 6, 0, 0)
        outer.addWidget(self.header)
        outer.addWidget(self.body)
        self.header.setChecked(not collapsed)
        self._apply(not collapsed)
        self.header.toggled.connect(self._apply)

    def _apply(self, expanded):
        self.header.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)
        self.body.setVisible(expanded)
        self.updateGeometry()
        self.collapsedChanged.emit(not expanded)

    def set_collapsed(self, collapsed):
        self.header.setChecked(not collapsed)

    def is_collapsed(self):
        return not self.header.isChecked()
