"""Settings controls that leave wheel gestures to their scrolling parent."""
from PySide6 import QtCore, QtGui, QtWidgets


def scroll_parent(control, event):
    ancestor = control.parentWidget()
    while ancestor is not None:
        if isinstance(ancestor, QtWidgets.QAbstractScrollArea):
            viewport = ancestor.viewport()
            forwarded = QtGui.QWheelEvent(
                QtCore.QPointF(viewport.mapFromGlobal(event.globalPosition().toPoint())),
                event.globalPosition(), event.pixelDelta(), event.angleDelta(),
                event.buttons(), event.modifiers(), event.phase(), event.inverted(),
                event.source(), event.pointingDevice(),
            )
            QtWidgets.QApplication.sendEvent(viewport, forwarded)
            event.setAccepted(forwarded.isAccepted())
            return
        ancestor = ancestor.parentWidget()
    event.ignore()


class NoWheelComboBox(QtWidgets.QComboBox):
    def wheelEvent(self, event):
        scroll_parent(self, event)


class NoWheelSlider(QtWidgets.QSlider):
    def wheelEvent(self, event):
        scroll_parent(self, event)
