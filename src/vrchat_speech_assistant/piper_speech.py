"""Optional Piper CLI integration using locally supplied voice assets."""
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import wave

from vrchat_speech_assistant.windows_speech import LocalSynthesisError


class PiperSpeech:
    def __init__(self, model, executable=""):
        self.model = model
        self.executable = executable

    def render(self, text, path, rate=100):
        try:
            if not self.model:
                raise ValueError("Choose a Piper model first")
            model = Path(self.model).resolve()
            if not model.is_file() or not Path(str(model) + ".json").is_file():
                raise ValueError("Piper needs both .onnx and .onnx.json voice assets")
            command = [sys.executable, "-m", "piper"]
            if self.executable or getattr(sys, "frozen", False):
                backend = self.executable or shutil.which("piper")
                if not backend or not Path(backend).is_file():
                    raise ValueError("Install Piper separately and select its piper.exe backend")
                command = [str(Path(backend).resolve())]
            # No shell interpolation, automatic downloads, or text in argv/logs.
            subprocess.run(
                [*command, "--model", str(model),
                 "--config", str(model) + ".json", "--output-file", str(path),
                 "--length-scale", str(100 / max(50, min(200, rate)))],
                input=text, encoding="utf-8", stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE, check=True, timeout=120,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            with wave.open(str(path), "rb") as audio:
                if audio.getnframes() == 0:
                    raise ValueError("Piper produced empty audio")
        except Exception as error:
            raise LocalSynthesisError("Piper synthesis failed; check installation and voice assets") from error

    def speech(self, text, voice_id, output_device_name, extra_tags=None):
        from vrchat_speech_assistant.providers import read_ogg_file
        with tempfile.TemporaryDirectory(prefix="vrcpiper-") as directory:
            path = Path(directory) / "speech.wav"
            self.render(text, path, rate=(extra_tags or {}).get("rate", 100))
            read_ogg_file(str(path), output_device_name)
