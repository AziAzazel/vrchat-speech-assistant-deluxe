"""Build a one-file Windows x64 executable from a clean Windows environment."""
from pathlib import Path
import sys
import os
from importlib.metadata import version


def main():
    if sys.platform != "win32":
        raise SystemExit("Build the Windows executable on Windows; cross-compilation is unsupported.")
    reference = os.getenv("GITHUB_REF", "")
    if reference.startswith("refs/tags/"):
        assert reference.removeprefix("refs/tags/") == "v" + version("vrchat_speech_assistant"), "Tag/version mismatch"
    import PyInstaller.__main__
    from third_party_notices import write_notices
    root = Path(__file__).resolve().parents[1]
    notices = root / "dist/THIRD_PARTY_NOTICES.txt"
    write_notices(notices)
    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "VRChatSpeechAssistantDeluxe", "--paths", str(root / "src"),
        "--distpath", str(root / "dist"), "--workpath", str(root / ".build_win" / "work"),
        "--specpath", str(root / ".build_win"),
        "--icon", str(root / "src/vrchat_speech_assistant/resources/logo.ico"),
        "--add-data", str(root / "src/vrchat_speech_assistant/resources") + ";vrchat_speech_assistant/resources",
        "--add-data", str(root / "LICENSE") + ";.",
        "--add-data", str(notices) + ";.",
        "--copy-metadata", "vrchat_speech_assistant",
        "--copy-metadata", "pywin32", "--copy-metadata", "pygame",
        "--collect-data", "botocore", "--collect-data", "boto3",
        "--hidden-import", "pythoncom", "--hidden-import", "pywintypes",
        "--hidden-import", "win32com.client", "--hidden-import", "pyaudio",
        "--hidden-import", "speech_recognition.recognizers.google",
        "--exclude-module", "vrchat_speech_assistant._config",
        "--exclude-module", "piper", "--exclude-module", "onnxruntime",
        str(root / "scripts/windows_launcher.py"),
    ])


if __name__ == "__main__":
    main()
