"""Section titles must stay above their first row, including larger fonts."""
import pytest
from PySide6 import QtCore, QtGui, QtWidgets
from vrchat_speech_assistant import darkstyle
from vrchat_speech_assistant.workspace_ui import form_group


@pytest.mark.parametrize('point_size', [9, 12, 18])
@pytest.mark.parametrize('width', [350, 650, 1100])
@pytest.mark.parametrize('enabled', [True, False])
def test_section_title_clears_content_at_different_fonts_and_widths(gui, point_size, width, enabled):
    app, _ = gui
    font = QtGui.QFont(app.font())
    font.setPointSize(point_size)
    page = QtWidgets.QWidget()
    page.setStyleSheet(darkstyle.STYLESHEET)
    page.setFont(font)
    layout = QtWidgets.QVBoxLayout(page)
    groups = []
    for title in ('Languages & translation', 'Recognition preview', 'Roleplay & pronunciation', 'Audio devices'):
        field = QtWidgets.QComboBox()
        field.addItem('Selected setting')
        group = form_group(title, [('First setting', field)])
        group.setEnabled(enabled)
        layout.addWidget(group)
        groups.append(group)
    # Rebuilt Speech/Chatbox forms contain untitled groups; they must not gain
    # the title-sized empty strip reserved for a real section header.
    plain = form_group('', [('Setting', QtWidgets.QLineEdit('Value'))])
    layout.addWidget(plain)
    page.resize(width, 700)
    page.show()
    app.processEvents()
    try:
        for group in groups:
            option = QtWidgets.QStyleOptionGroupBox()
            group.initStyleOption(option)
            title = group.style().subControlRect(QtWidgets.QStyle.CC_GroupBox, option,
                                                QtWidgets.QStyle.SC_GroupBoxLabel, group)
            assert group.rect().contains(title), group.title()
            for widget in group.findChildren(QtWidgets.QWidget):
                if widget.isVisible():
                    rect = QtCore.QRect(widget.mapTo(group, QtCore.QPoint()), widget.size())
                    assert rect.top() > title.bottom() + 6, (group.title(), rect, title)
        plain_top = min(widget.geometry().top() for widget in plain.findChildren(QtWidgets.QWidget) if widget.isVisible())
        titled_top = min(widget.geometry().top() for widget in groups[0].findChildren(QtWidgets.QWidget) if widget.isVisible())
        assert plain_top < titled_top / 2
    finally:
        page.close()
        page.deleteLater()


def test_heading_gap_updates_when_the_font_changes(gui):
    app, _ = gui
    field = QtWidgets.QLineEdit('Value')
    group = form_group('Recognition preview', [('First setting', field)])
    group.setStyleSheet(darkstyle.STYLESHEET)
    group.show()
    try:
        for point_size in (9, 18, 12):
            font = QtGui.QFont(app.font())
            font.setPointSize(point_size)
            group.setFont(font)
            app.processEvents()
            option = QtWidgets.QStyleOptionGroupBox()
            group.initStyleOption(option)
            title = group.style().subControlRect(QtWidgets.QStyle.CC_GroupBox, option,
                                                QtWidgets.QStyle.SC_GroupBoxLabel, group)
            assert field.geometry().top() > title.bottom() + 6
    finally:
        group.close()
        group.deleteLater()
