"""Single-chord recording while the application's own shortcuts are suspended."""
from PySide6 import QtCore, QtGui, QtWidgets


class ShortcutEdit(QtWidgets.QLineEdit):
    def __init__(self, sequence=None, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText('Click and press shortcut')
        self.setToolTip('Press one shortcut. Backspace or Delete clears it.')
        self.setKeySequence(sequence or QtGui.QKeySequence())

    def keySequence(self):
        return QtGui.QKeySequence(self.text(), QtGui.QKeySequence.PortableText)

    def setKeySequence(self, sequence):
        self.setText(sequence.toString(QtGui.QKeySequence.PortableText))

    def event(self, event):
        if event.type() == QtCore.QEvent.ShortcutOverride:
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() in (QtCore.Qt.Key_Control, QtCore.Qt.Key_Shift, QtCore.Qt.Key_Alt,
                           QtCore.Qt.Key_Meta, QtCore.Qt.Key_AltGr):
            event.accept()
            return
        if event.key() in (QtCore.Qt.Key_Backspace, QtCore.Qt.Key_Delete) and not event.modifiers():
            self.clear()
        else:
            self.setKeySequence(QtGui.QKeySequence(event.keyCombination()))
        event.accept()


class HotkeySettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._hotkey_window = parent
        self._holding_keys = False
        self.finished.connect(self._restore_keys)

    def showEvent(self, event):
        if not self._holding_keys:
            self._holding_keys = True
            self._hotkey_window._hotkey_edit_depth += 1
            self._hotkey_window._init_hotkeys()
        super().showEvent(event)

    def _restore_keys(self, *args):
        if self._holding_keys:
            self._holding_keys = False
            self._hotkey_window._hotkey_edit_depth -= 1
            if not self._hotkey_window._closing:
                self._hotkey_window._init_hotkeys()
