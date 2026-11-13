"""Small platform boundary for defaults and notification audio."""
import sys
import os
from PySide6 import QtCore

IS_WINDOWS = sys.platform == 'win32'
DEFAULT_PROVIDER = 'Windows Speech' if IS_WINDOWS else 'Piper (offline)'


def external_process_env():
    environment = dict(os.environ)
    if sys.platform.startswith('linux') and getattr(sys, 'frozen', False):
        original = environment.pop('LD_LIBRARY_PATH_ORIG', None)
        if original is None:
            environment.pop('LD_LIBRARY_PATH', None)
        else:
            environment['LD_LIBRARY_PATH'] = original
    return environment


class NotificationPlayer(QtCore.QObject):
    """Always called on the GUI thread; independent from the speech mixer."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sounds = {}

    @QtCore.Slot(str)
    def play(self, path):
        if IS_WINDOWS:
            import winsound
            winsound.PlaySound(path, winsound.SND_ASYNC)
        else:
            from PySide6.QtMultimedia import QSoundEffect
            if path not in self.sounds:
                sound = QSoundEffect(self)
                sound.setSource(QtCore.QUrl.fromLocalFile(path))
                sound.setVolume(.35)
                self.sounds[path] = sound
            self.sounds[path].play()
