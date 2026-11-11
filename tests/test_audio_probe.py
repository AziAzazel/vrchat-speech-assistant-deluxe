"""Keep PortAudio enumeration out of the capture process, including failures."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from vrchat_speech_assistant import audio_devices


def test_probe_runs_in_separate_process_without_parent_portaudio(monkeypatch):
    parent_audio = Mock(side_effect=AssertionError('Parent PortAudio must not be touched'))
    monkeypatch.setitem(sys.modules, 'pyaudio', SimpleNamespace(PyAudio=parent_audio))
    # Run the real process boundary with a fake enumerator, independent of hardware.
    code = ('import json,os,sys; from pathlib import Path; '
            'Path(sys.argv[1]).write_text(json.dumps({"inputs": [{"name": "Mikrofon ł", "index": 0}], '
            '"outputs": [], "pid": os.getpid(), "appdata": os.environ["APPDATA"]}), encoding="utf-8")')
    monkeypatch.setattr(audio_devices, '_probe_command', lambda report: [sys.executable, '-c', code, str(report)])
    snapshot = audio_devices.get_device_snapshot()
    assert snapshot['pid'] != os.getpid()
    assert snapshot['inputs'][0]['index'] == 0
    assert snapshot['inputs'][0]['name'] == 'Mikrofon ł'
    assert snapshot['appdata'] != os.environ['APPDATA']
    assert not Path(snapshot['appdata']).exists()
    parent_audio.assert_not_called()


def test_abrupt_probe_exit_does_not_crash_parent(monkeypatch):
    monkeypatch.setattr(audio_devices, '_probe_command', lambda report: [sys.executable, '-c', 'import os; os._exit(139)'])
    with pytest.raises(RuntimeError, match='probe exited'):
        audio_devices.get_device_snapshot()


@pytest.mark.parametrize('payload', [{}, {'inputs': None, 'outputs': []},
                                      {'inputs': [{'name': 'Mic', 'index': -1}], 'outputs': []}])
def test_invalid_probe_report_is_rejected(monkeypatch, payload):
    def run(command, **kwargs):
        Path(command[-1]).write_text(json.dumps(payload), encoding='utf-8')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(audio_devices.subprocess, 'run', run)
    with pytest.raises(ValueError):
        audio_devices.get_device_snapshot()


def test_hung_probe_has_deadline_and_no_console(monkeypatch):
    def timeout(command, **kwargs):
        assert kwargs['timeout'] == 30
        assert kwargs['stdin'] == subprocess.DEVNULL
        assert kwargs['stderr'] == subprocess.DEVNULL
        raise subprocess.TimeoutExpired(command, 30)
    monkeypatch.setattr(audio_devices.subprocess, 'run', timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        audio_devices.get_device_snapshot()


def test_frozen_probe_reuses_executable_not_gui(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    assert audio_devices._probe_command(Path('report.json')) == [sys.executable, '--audio-device-probe', 'report.json']

