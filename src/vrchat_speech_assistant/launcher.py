"""Shared GUI startup with platform-specific command-line integration."""
import sys


def run_gui():
    from PySide6 import QtWidgets
    from vrchat_speech_assistant import darkstyle
    from vrchat_speech_assistant.main import VRCSpeechAssistantWindow
    app = QtWidgets.QApplication(sys.argv[:1])
    darkstyle.apply(app)
    window = VRCSpeechAssistantWindow()
    window.show()
    return app.exec()


def main():
    if sys.platform.startswith('linux'):
        from vrchat_speech_assistant.linux_launcher import main as linux_main
        return linux_main()
    return run_gui()
