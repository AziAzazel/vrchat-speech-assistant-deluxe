"""Entry point for the standalone Windows executable and its build smoke test."""
import json
import os
from pathlib import Path
import sys
import tempfile
import wave

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def smoke_test(report):
    os.environ["APPDATA"] = tempfile.mkdtemp(prefix="deluxe-smoke-")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    from vrchat_speech_assistant._version import __version__
    from vrchat_speech_assistant.main import VRCSpeechAssistantWindow, RESOURCES_PATH
    from vrchat_speech_assistant.windows_speech import WindowsSpeech
    from vrchat_speech_assistant import darkstyle
    from vrchat_speech_assistant.piper_speech import PiperSpeech
    for filename in ("banner.png", "logo.png", "on.wav", "off.wav"):
        assert (RESOURCES_PATH / filename).is_file(), filename
    speech = WindowsSpeech()
    assert speech.voices, "No SAPI desktop voices on build runner"
    path = Path(os.environ["APPDATA"]) / "sapi.wav"
    speech.render("Speech assistant build verification.", next(iter(speech.voices)), path)
    with wave.open(str(path)) as audio:
        assert audio.getnframes() > 0
    app = QtWidgets.QApplication([])
    darkstyle.apply(app)
    window = VRCSpeechAssistantWindow()
    window.show()
    app.processEvents()
    assert window.isVisible()
    assert window.config["SPEECH"]["provider"] == "Windows Speech"
    window.close()
    app.processEvents()
    Path(report).write_text(json.dumps({"version": __version__, "gui": "passed", "sapi_wav": "passed", "resources": "passed"}), encoding="utf-8")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        smoke_test(sys.argv[2])
        return 0
    from PySide6 import QtWidgets
    from vrchat_speech_assistant import darkstyle
    from vrchat_speech_assistant.main import VRCSpeechAssistantWindow
    app = QtWidgets.QApplication([])
    darkstyle.apply(app)
    window = VRCSpeechAssistantWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
