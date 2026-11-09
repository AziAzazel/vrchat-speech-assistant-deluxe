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
