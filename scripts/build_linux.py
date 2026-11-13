"""Build a portable Linux x86-64 directory; the host supplies its audio server."""
from pathlib import Path
from importlib.metadata import version
import os
import platform
import sys
import tarfile
import shutil


def main():
    if not sys.platform.startswith('linux') or platform.machine() != 'x86_64':
        raise SystemExit('Build the Linux x86-64 package on Linux x86-64.')
    release = version('vrchat_speech_assistant')
    reference = os.getenv('GITHUB_REF', '')
    if reference.startswith('refs/tags/'):
        assert reference.removeprefix('refs/tags/') == 'v' + release, 'Tag/version mismatch'
    import PyInstaller.__main__
    from third_party_notices import write_notices
    root = Path(__file__).resolve().parents[1]
    target = root/'dist/linux'
    notices = target/'THIRD_PARTY_NOTICES.txt'
    write_notices(notices)
    PyInstaller.__main__.run([
        '--noconfirm', '--clean', '--onedir', '--name', 'VRChatSpeechAssistantDeluxe',
        '--paths', str(root/'src'), '--distpath', str(target),
        '--workpath', str(root/'.build_linux/work'), '--specpath', str(root/'.build_linux'),
        '--additional-hooks-dir', str(root/'scripts/pyinstaller_hooks'),
        '--add-data', str(root/'src/vrchat_speech_assistant/resources') + ':vrchat_speech_assistant/resources',
        '--add-data', str(root/'LICENSE') + ':.', '--add-data', str(notices) + ':.',
        '--copy-metadata', 'vrchat_speech_assistant', '--copy-metadata', 'pygame',
        '--collect-data', 'boto3', '--hidden-import', 'pyaudio',
        '--hidden-import', 'pygame._sdl2.audio', '--hidden-import', 'pygame._sdl2.sdl2',
        '--hidden-import', 'speech_recognition.recognizers.google',
        '--exclude-module', 'vrchat_speech_assistant._config', '--exclude-module', 'piper',
        '--exclude-module', 'onnxruntime', str(root/'scripts/linux_launcher.py'),
    ])
    folder = target/'VRChatSpeechAssistantDeluxe'
    for source in (notices, root/'LICENSE', root/'docs/LINUX.md'):
        shutil.copy2(source, folder/source.name)
    guide = folder/'LINUX.md'
    guide.write_text(guide.read_text().replace('(../README.md)', '(https://github.com/AziAzazel/vrchat-speech-assistant-deluxe)')
        .replace('(USAGE.md)', '(https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/blob/master/docs/USAGE.md)')
        .replace('(../CHANGELOG.md)', '(https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/blob/master/CHANGELOG.md)'))
    start = folder/'start.sh'
    start.write_text('#!/bin/sh\ncd -- "$(dirname -- "$0")" || exit 1\nexec ./VRChatSpeechAssistantDeluxe "$@"\n')
    start.chmod(0o755)
    with tarfile.open(target/f'VRChatSpeechAssistantDeluxe-{release}-linux-x86_64.tar.gz', 'w:gz') as archive:
        archive.add(folder, arcname=folder.name)


if __name__ == '__main__':
    main()
