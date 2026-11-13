"""PyInstaller Linux entry point with isolated packaged smoke settings."""
import os
import sys
import tempfile
if '--smoke-test' in sys.argv:
    os.environ['APPDATA'] = tempfile.mkdtemp(prefix='deluxe-linux-smoke-')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from vrchat_speech_assistant.linux_launcher import main

if __name__ == '__main__':
    raise SystemExit(main())
