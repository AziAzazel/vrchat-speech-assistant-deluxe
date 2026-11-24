"""Per-output cooperative cancellation, isolated from subsequent utterances."""
from contextlib import contextmanager
import subprocess
import threading
import time

_state = threading.local()


class OutputCancelled(Exception):
    pass


@contextmanager
def output_scope(event):
    previous = getattr(_state, "event", None)
    _state.event = event
    try:
        yield
    finally:
        _state.event = previous


def cancellation_event():
    return getattr(_state, "event", None)


def check_cancelled():
    event = cancellation_event()
    if event and event.is_set():
        raise OutputCancelled()


@contextmanager
def playback_scope(callback):
    previous = getattr(_state, 'playback', None)
    _state.playback = callback
    try:
        yield
    finally:
        _state.playback = previous


def playback_callback():
    return getattr(_state, 'playback', None)


@contextmanager
def generated_audio_scope(callback):
    previous = getattr(_state, 'generated_audio', None)
    _state.generated_audio = callback
    try:
        yield
    finally:
        _state.generated_audio = previous


def report_generated_audio(path):
    callback = getattr(_state, 'generated_audio', None)
    if callback is not None:
        callback(path)


@contextmanager
def audio_delivery_scope(router):
    previous = getattr(_state, 'audio_delivery', None)
    _state.audio_delivery = router
    try:
        yield
    finally:
        _state.audio_delivery = previous


def audio_delivery_callback():
    return getattr(_state, 'audio_delivery', None)


class CancellableOSC:
    def __init__(self, client):
        self.client = client

    def send_message(self, *args, **kwargs):
        check_cancelled()
        return self.client.send_message(*args, **kwargs)


def run_process(argv, **kwargs):
    event = cancellation_event()
    if event is None:
        return subprocess.run(argv, **kwargs)
    check_cancelled()
    text = kwargs.pop("input", None)
    check = kwargs.pop("check", False)
    timeout = kwargs.pop("timeout", 120)
    started = time.monotonic()
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, **kwargs)
    try:
        first = True
        while True:
            check_cancelled()
            try:
                out, err = process.communicate(input=text if first else None, timeout=.1)
                break
            except subprocess.TimeoutExpired:
                first = False
                if time.monotonic() - started > timeout:
                    raise subprocess.TimeoutExpired(argv, timeout)
        check_cancelled()
        if check and process.returncode:
            raise subprocess.CalledProcessError(process.returncode, argv, out, err)
        return subprocess.CompletedProcess(argv, process.returncode, out, err)
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate()
