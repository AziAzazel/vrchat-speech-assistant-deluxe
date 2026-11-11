"""Enumerate in a disposable process: PortAudio lifecycle is not thread-safe.

Never initialize/terminate a second PortAudio context beside microphone capture.
The GUI only consumes JSON; a native crash or hung driver stays in the probe.
"""
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def _probe_command(report):
    if getattr(sys, "frozen", False):
        return [sys.executable, "--audio-device-probe", str(report)]
    return [sys.executable, "-m", "vrchat_speech_assistant.audio_devices", str(report)]


def get_device_snapshot():
    with tempfile.TemporaryDirectory(prefix="deluxe-audio-probe-") as directory:
        report = Path(directory) / "devices.json"
        environment = dict(os.environ, APPDATA=directory)
        completed = subprocess.run(
            _probe_command(report), env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=30,
        )
        if completed.returncode:
            logging.getLogger("deluxe.audio_devices").warning(
                "Audio device probe exited; code=%s", completed.returncode)
            raise RuntimeError("Audio device probe exited unsuccessfully")
        snapshot = json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(snapshot, dict):
            raise ValueError("Invalid audio device snapshot")
        for kind in ("inputs", "outputs"):
            devices = snapshot.get(kind)
            if not isinstance(devices, list) or any(
                not isinstance(d, dict) or not isinstance(d.get("name"), str)
                or type(d.get("index")) is not int or d["index"] < 0 for d in devices
            ):
                raise ValueError("Invalid audio device snapshot")
        return snapshot


def write_device_probe(report):
    if sys.platform == "win32":
        import ctypes
        # Do not display a Windows crash dialog if a driver fails in the helper.
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)
    snapshot = {"inputs": _get_devices_in_probe("input"),
                "outputs": _get_devices_in_probe("output"), "pid": os.getpid()}
    Path(report).write_text(json.dumps(snapshot), encoding="utf-8")


def _get_devices_in_probe(device_type):
    import pyaudio
    context = pyaudio.PyAudio()
    try:
        preferred = pyaudio.paMME if device_type == "input" else pyaudio.paWASAPI
        try:
            api = context.get_host_api_info_by_type(preferred)["index"]
        except OSError:
            api = None
        channel = "maxInputChannels" if device_type == "input" else "maxOutputChannels"
        devices = [context.get_device_info_by_index(i) for i in range(context.get_device_count())]
        devices = [d for d in devices if d.get(channel, 0) > 0 and "Microsoft Sound Mapper" not in d["name"]]
        matching = [d for d in devices if d.get("hostApi") == api]
        selected = matching or devices
        return sorted({d["name"]: d for d in selected}.values(), key=lambda d: d["name"])
    finally:
        context.terminate()


if __name__ == "__main__":
    write_device_probe(sys.argv[1])
