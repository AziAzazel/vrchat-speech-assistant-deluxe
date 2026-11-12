"""Deduplicated, atomic INI persistence with explicit batches for UI updates."""
from contextlib import contextmanager
from functools import wraps
import hashlib
import io
import os
from pathlib import Path
import tempfile


class SettingsStore:
    def __init__(self, path, on_error=None):
        self.path = Path(path)
        self.on_error = on_error
        self._digest = None
        self._signature = None
        self._depth = 0
        self._pending = None

    def _file_signature(self):
        try:
            stat = self.path.stat()
            return stat.st_mtime_ns, stat.st_size
        except FileNotFoundError:
            return None

    def save(self, config):
        stream = io.StringIO()
        config.write(stream)
        text = stream.getvalue()
        if self._depth:
            self._pending = text
            return False
        return self._persist(text)

    @contextmanager
    def batch(self):
        previous = self._pending
        self._depth += 1
        try:
            yield
        except BaseException:
            self._pending = previous
            raise
        finally:
            self._depth -= 1
            if not self._depth and self._pending is not None:
                text, self._pending = self._pending, None
                self._persist(text)

    def _persist(self, text):
        try:
            return self._commit(text.encode('utf-8'))
        except OSError as error:
            if self.on_error is None:
                raise
            self.on_error(error)
            return False

    def _commit(self, content):
        digest = hashlib.sha256(content).digest()
        signature = self._file_signature()
        if digest == self._digest and signature is not None and signature == self._signature:
            return False
        if signature is not None and self.path.read_bytes() == content:
            self._digest, self._signature = digest, signature
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=self.path.name + '.', suffix='.tmp', dir=self.path.parent)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(content)
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        self._digest, self._signature = digest, self._file_signature()
        return True


def batch_settings(method):
    @wraps(method)
    def batched(window, *args, **kwargs):
        with window._settings_store.batch():
            return method(window, *args, **kwargs)
    return batched
