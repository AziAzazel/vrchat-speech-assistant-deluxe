"""Native Linux entry point, packaged probe and focus-independent action sender."""
import argparse
import json
import os
from pathlib import Path
import re
import sys


def send_action(action):
    from vrchat_speech_assistant.roleplay import ACTIONS
    if action not in ACTIONS and not re.fullmatch(r'soundboard_(?:[0-9]|[12][0-9]|3[01])', action):
        raise ValueError('Use a Roleplay action name or soundboard_0 through soundboard_31.')
    from pythonosc.udp_client import SimpleUDPClient
    SimpleUDPClient('127.0.0.1', 7001).send_message('/roleplay', action)


def install_desktop():
    if not getattr(sys, 'frozen', False):
        raise ValueError('Use --install-desktop from the downloaded Linux executable.')
    executable = str(Path(sys.executable).resolve())
    for character in ('\\', '"', '`', '$'):
        executable = executable.replace(character, '\\' + character)
    executable = executable.replace('%', '%%')
    icon = Path(__file__).parent / 'resources' / 'logo.png'
    target = Path(os.getenv('XDG_DATA_HOME') or Path.home()/'.local/share')/'applications/vrchat-speech-assistant-deluxe.desktop'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('[Desktop Entry]\nType=Application\nName=VRChat Speech Assistant Deluxe\n'
                      f'Exec="{executable}"\nIcon={icon}\nTerminal=false\nCategories=AudioVideo;Audio;\n', encoding='utf-8')
    return target


def main(argv=None):
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')
    parser = argparse.ArgumentParser(description='VRChat Speech Assistant Deluxe for Linux')
    parser.add_argument('--action', help='Send a local action to a running Deluxe instance (KDE global shortcut).')
    parser.add_argument('--install-desktop', action='store_true', help='Add a menu launcher for this portable installation.')
    parser.add_argument('--audio-device-probe', metavar='REPORT', help=argparse.SUPPRESS)
    parser.add_argument('--smoke-test', metavar='REPORT', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.audio_device_probe:
            from vrchat_speech_assistant.audio_devices import write_device_probe
            write_device_probe(args.audio_device_probe)
            return 0
        if args.action:
            send_action(args.action)
            print('Action sent to Deluxe on localhost:7001. Keep the main application running.')
            return 0
        if args.install_desktop:
            print(install_desktop())
            return 0
        if args.smoke_test:
            from vrchat_speech_assistant.linux_smoke import smoke_test
            smoke_test(args.smoke_test)
            return 0
        from vrchat_speech_assistant.launcher import run_gui
        return run_gui()
    except Exception as error:
        from vrchat_speech_assistant.diagnostics import record_failure
        record_failure('Linux launcher', type(error), error.__traceback__)
        if args.smoke_test:
            import traceback
            target = Path(args.smoke_test)
            details = json.loads(target.read_text()) if target.exists() else {}
            details.update(status='failed', exception=type(error).__name__, frames=[
                {'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                for f in traceback.extract_tb(error.__traceback__)])
            target.write_text(json.dumps(details), encoding='utf-8')
        print('Could not complete the request. See ~/.config/VRChat Speech Assistant/logs (or XDG_CONFIG_HOME).', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
