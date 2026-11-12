import json
import os
import subprocess
import sys


def test_local_startup_modules_do_not_import_cloud_sdks(tmp_path):
    code = ('import sys,json; from vrchat_speech_assistant import providers,utils; '
            'assert utils.test_deepl("") is None; '
            'print(json.dumps({"boto3": "boto3" in sys.modules,"deepl":"deepl" in sys.modules,"pygame":"pygame" in sys.modules}))')
    environment = dict(os.environ, APPDATA=str(tmp_path), PYGAME_HIDE_SUPPORT_PROMPT='1')
    result = subprocess.run([sys.executable, '-c', code], env=environment, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout.strip()) == {'boto3': False, 'deepl': False, 'pygame': False}
