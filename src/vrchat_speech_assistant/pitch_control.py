"""Pitch slider with a zero detent and a visible SSML/local range legend."""
from PySide6 import QtCore, QtGui, QtWidgets
from vrchat_speech_assistant.wheel_controls import NoWheelSlider
from vrchat_speech_assistant.audio_effects import MIN_PITCH, MAX_PITCH
from vrchat_speech_assistant.pitch_routing import pitch_route, ssml_pitch_available, SSML_MIN_PITCH, SSML_MAX_PITCH

SSML_COLOR, LOCAL_COLOR = '#64b5f6', '#ffb74d'


class PitchSlider(NoWheelSlider):
    def __init__(self, parent=None):
        super().__init__(QtCore.Qt.Horizontal, parent)
        self.setRange(MIN_PITCH, MAX_PITCH)
        self.setMinimumHeight(28)
        self.setAccessibleName('Voice pitch')

    def _snap_zero(self):
        if abs(self.value()) <= 3:
            self.setValue(0)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.isSliderDown():
            self._snap_zero()

    def mouseReleaseEvent(self, event):
        # Snap before sliderReleased so the existing persistence hook saves zero.
        if self.isSliderDown():
            self._snap_zero()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.setValue(0)
        event.accept()

    def paintEvent(self, event):
        super().paintEvent(event)
        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        handle = self.style().subControlRect(QtWidgets.QStyle.CC_Slider, option, QtWidgets.QStyle.SC_SliderHandle, self)
        position = QtWidgets.QStyle.sliderPositionFromValue(self.minimum(), self.maximum(), 0,
                                                          self.width() - handle.width(), option.upsideDown)
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QColor('#eeeeee'))
        x = position + handle.width() // 2
        painter.drawLine(x, self.height() - 6, x, self.height() - 1)


class PitchControl(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.provider, self.voice = '', ''
        self.slider = PitchSlider(self)
        self.value_label = QtWidgets.QLabel()
        self.value_label.setMinimumWidth(105)
        self.reset = QtWidgets.QToolButton()
        self.reset.setText('0%')
        self.reset.setToolTip('Reset pitch to 0% (natural voice). You can also double-click the slider.')
        self.reset.clicked.connect(lambda: self.slider.setValue(0))
        self.legend = QtWidgets.QLabel()
        self.legend.setWordWrap(True)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.slider, 1)
        row.addWidget(self.value_label)
        row.addWidget(self.reset)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(row)
        layout.addWidget(self.legend)
        self.slider.valueChanged.connect(self._refresh)
        self.configure('', '')

    def configure(self, provider, voice):
        self.provider, self.voice = provider, voice
        self._refresh()

    def _refresh(self):
        route = pitch_route(self.provider, self.voice, self.slider.value())
        available = ssml_pitch_available(self.provider, self.voice)
        color = SSML_COLOR if route == 'ssml' else LOCAL_COLOR if route == 'local' else '#eeeeee'
        text = {'ssml': 'SSML', 'local': 'Local', 'off': 'Natural'}[route]
        self.value_label.setText(f'{self.slider.value():+d}% · {text}' if self.slider.value() else '0% · Natural')
        self.value_label.setStyleSheet(f'color: {color};')
        if available:
            start = (SSML_MIN_PITCH - MIN_PITCH) / (MAX_PITCH - MIN_PITCH)
            end = (SSML_MAX_PITCH - MIN_PITCH) / (MAX_PITCH - MIN_PITCH)
            track = (f'qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {LOCAL_COLOR},'
                     f'stop:{start-.0001:.5f} {LOCAL_COLOR},stop:{start:.5f} {SSML_COLOR},'
                     f'stop:{end:.5f} {SSML_COLOR},stop:{end+.0001:.5f} {LOCAL_COLOR},stop:1 {LOCAL_COLOR})')
            legend = (f'<span style="color:{SSML_COLOR}">Blue: Polly SSML −50…+50%</span> · '
                      f'<span style="color:{LOCAL_COLOR}">Orange: local outside this range</span>')
        else:
            track = LOCAL_COLOR
            legend = f'<span style="color:{LOCAL_COLOR}">Orange: local pitch throughout the range (this voice)</span>'
        self.legend.setText(legend)
        self.slider.setProperty('pitchRoute', route)
        self.slider.setStyleSheet(
            f'QSlider::groove:horizontal {{height:6px;background:{track};border-radius:3px;}}'
            'QSlider::sub-page:horizontal,QSlider::add-page:horizontal {background:transparent;}'
            f'QSlider::handle:horizontal {{width:14px;height:16px;margin:-6px 0;border:1px solid #222;border-radius:4px;background:{color};}}')
        tip = ('Pitch −75%…+300%. Blue: Polly Standard SSML from −50% through +50%; orange: local processing. '
               'Neural, Windows Speech and Piper always use local pitch. 0% keeps the natural voice. '
               'Drag near zero to snap, double-click, or use the 0% button. Audio export includes the selected effect.')
        self.slider.setToolTip(tip)
        self.slider.setAccessibleDescription(self.value_label.text())
