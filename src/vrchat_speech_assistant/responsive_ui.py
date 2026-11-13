"""Reflow whole control sections into one, two or three columns."""
from PySide6 import QtCore, QtWidgets


class ResponsiveCards(QtWidgets.QWidget):
    def __init__(self, cards, parent=None):
        super().__init__(parent)
        self.cards = cards
        self._viewport = None
        self.columns = 0
        self.grid = QtWidgets.QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.grid.setAlignment(QtCore.Qt.AlignTop)
        self.reflow()

    def reflow(self):
        # Grid minimum widths can exceed the visible area (notably with Windows
        # font metrics). Do not use that overflow to select still more columns.
        width = self.width()
        if self._viewport is not None:
            width = self._viewport.width()
            parent_layout = self.parentWidget().layout()
            if parent_layout is not None:
                margins = parent_layout.contentsMargins()
                width -= margins.left() + margins.right()
        columns = max(1, min(3, width // 400))
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

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QtCore.QSize(0, hint.height())

    def showEvent(self, event):
        super().showEvent(event)
        ancestor = self.parentWidget()
        while ancestor is not None and not isinstance(ancestor, QtWidgets.QScrollArea):
            ancestor = ancestor.parentWidget()
        viewport = ancestor.viewport() if ancestor is not None else None
        if viewport is not self._viewport:
            if self._viewport is not None:
                self._viewport.removeEventFilter(self)
            self._viewport = viewport
            if viewport is not None:
                viewport.installEventFilter(self)
        self.reflow()

    def eventFilter(self, watched, event):
        if watched is self._viewport and event.type() == QtCore.QEvent.Resize:
            self.reflow()
        return super().eventFilter(watched, event)


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
