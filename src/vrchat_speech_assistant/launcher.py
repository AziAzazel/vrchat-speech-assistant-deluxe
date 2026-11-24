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
    if len(sys.argv) == 3 and sys.argv[1] in ('--live-voice-worker','--live-voice-probe'):
        from vrchat_speech_assistant.live_worker import main as live_main
        return live_main(sys.argv[1:])
    if sys.platform.startswith('linux'):
        from vrchat_speech_assistant.linux_launcher import main as linux_main
        return linux_main()
    return run_gui()
