"""YouTube link controls and explicit Windows browser audio routing guidance."""
import os
import sys
from PySide6 import QtCore, QtWidgets
from vrchat_speech_assistant.diagnostics import DATA_DIR, record_failure
from vrchat_speech_assistant.youtube_player import EdgePlayer


class YouTubeDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('YouTube audio — Edge player')
        self.resize(680, 300)
        self.player = EdgePlayer(DATA_DIR / 'youtube-edge-profile')
        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel('Open YouTube in a separate Microsoft Edge player window. '
                                'Use the normal YouTube Play/Pause, timeline and volume controls. '
                                'No media files or captions are exported. Internet and installed Edge are required.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.url = QtWidgets.QLineEdit()
        self.url.setMaxLength(2048)
        self.url.setPlaceholderText('Paste a YouTube video link')
        self.url.returnPressed.connect(self.play)
        layout.addWidget(self.url)
        controls = QtWidgets.QHBoxLayout()
        for title, callback in [('Open / replace video', self.play), ('Stop YouTube', self.stop),
                                ('Windows volume mixer', self.open_mixer)]:
            button = QtWidgets.QPushButton(title)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.routing = QtWidgets.QLabel()
        self.routing.setWordWrap(True)
        layout.addWidget(self.routing)
        self.status = QtWidgets.QLabel('Ready. Nothing plays until you open a link and start playback in YouTube.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        footer = QtWidgets.QLabel('YouTube audio is separate from Speech output. Stop speaking stops both. '
                                  'Closing this panel also stops its player. Your ordinary Edge windows are left open.')
        footer.setWordWrap(True)
        layout.addWidget(footer)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.refresh_routing()

    def refresh_routing(self):
        device = self.parent().config['SPEECH'].get('output_device') or 'your virtual cable'
        self.routing.setText('To send the browser audio to VRChat: start playback, open Windows volume mixer, '
                             'and select ' + device + ' (or your virtual cable) as Microsoft Edge output. '
                             'The Speech device selector does not change Edge output. This Windows setting may affect other Edge windows too.')

    def play(self):
        if self.parent()._closing:
            return
        try:
            target = self.player.start(self.url.text())
            self.url.setText(target)
            self.status.setText('Edge player opened. Start playback in YouTube; consent, ads or sign-in may appear there.')
        except ValueError as error:
            self.status.setText(str(error))
        except Exception:
            record_failure('Start YouTube Edge player', *sys.exc_info()[::2])
            self.status.setText('Could not start a separate Edge player. See diagnostic logs.')

    def stop(self):
        try:
            self.player.stop()
            self.status.setText('YouTube stopped.')
        except Exception:
            record_failure('Stop YouTube Edge player', *sys.exc_info()[::2])
            self.status.setText('Could not stop the player. Close its Edge window; see diagnostic logs.')

    def poll(self):
        try:
            if not self.player.is_running:
                self.player.stop()
        except Exception:
            self.timer.stop()
            record_failure('Monitor YouTube Edge player', *sys.exc_info()[::2])
            self.status.setText('Player monitoring failed. Close its Edge window; see diagnostic logs.')

    def open_mixer(self):
        try:
            if sys.platform == 'win32':
                os.startfile('ms-settings:apps-volume')
        except OSError:
            self.status.setText('Open Windows Settings → System → Sound → Volume mixer to route Microsoft Edge audio.')

    def showEvent(self, event):
        self.timer.start(1000)
        super().showEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        self.stop()
        event.accept()
