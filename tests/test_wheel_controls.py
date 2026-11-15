"""Wheel navigation must scroll settings without editing focused values."""
import pytest
from PySide6 import QtCore, QtGui, QtWidgets, QtTest
from vrchat_speech_assistant.wheel_controls import NoWheelComboBox, NoWheelSlider


@pytest.mark.parametrize('kind', ['combo', 'slider'])
@pytest.mark.parametrize('focused', [False, True])
def test_wheel_scrolls_parent_without_changing_control(gui, kind, focused):
    app, _ = gui
    scroll = QtWidgets.QScrollArea()
    content = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(content)
    control = NoWheelComboBox() if kind == 'combo' else NoWheelSlider(QtCore.Qt.Horizontal)
    if kind == 'combo':
        control.addItems(['First', 'Second', 'Third'])
        control.setCurrentIndex(1)
        value = control.currentIndex
    else:
        control.setRange(0, 100)
        control.setValue(50)
        value = control.value
    layout.addWidget(control)
    layout.addWidget(QtWidgets.QLineEdit())
    layout.addStretch()
    content.setMinimumHeight(1000)
    scroll.setWidget(content)
    scroll.setWidgetResizable(True)
    scroll.resize(350, 200)
    scroll.show()
    app.processEvents()
    if focused:
        control.setFocus()
    else:
        scroll.setFocus()
    app.processEvents()
    assert control.hasFocus() == focused
    before = value()
    event = QtGui.QWheelEvent(QtCore.QPointF(control.rect().center()),
                             QtCore.QPointF(control.mapToGlobal(control.rect().center())),
                             QtCore.QPoint(), QtCore.QPoint(0, -120),
                             QtCore.Qt.NoButton, QtCore.Qt.NoModifier,
                             QtCore.Qt.NoScrollPhase, False)
    try:
        app.sendEvent(control, event)
        app.processEvents()
        assert value() == before
        assert scroll.verticalScrollBar().value() > 0
        # Explicit keyboard edits still work.
        control.setFocus()
        QtTest.QTest.keyClick(control, QtCore.Qt.Key_Down if kind == 'combo' else QtCore.Qt.Key_Right)
        assert value() == before + 1
    finally:
        scroll.close()
