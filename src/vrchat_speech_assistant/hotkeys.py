"""Windows registered hotkeys: no keyboard hooks or keystroke capture."""
import ctypes
from ctypes import wintypes
import sys
import threading


def parse_hotkey(sequence):
    parts = [part.strip().upper() for part in sequence.split("+")]
    modifiers = {"ALT": 1, "CTRL": 2, "SHIFT": 4, "WIN": 8, "META": 8}
    if not parts or any(part not in modifiers for part in parts[:-1]):
        raise ValueError("Use Ctrl/Alt/Shift/Win plus a letter, digit, punctuation key or F1–F24")
    flags = 0
    for part in parts[:-1]:
        flags |= modifiers[part]
    key = parts[-1]
    if key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        code = 111 + int(key[1:])
    elif len(key) == 1 and key.isascii() and key.isalnum() and flags:
        code = ord(key)
    elif flags and key in {";", "=", ",", "-", ".", "/", "`", "[", "\\", "]", "'"}:
        code = {";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD, ".": 0xBE,
                "/": 0xBF, "`": 0xC0, "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE}[key]
        if sys.platform == "win32":
            mapped = ctypes.windll.user32.VkKeyScanW(ord(key))
            if mapped == -1:
                raise ValueError("This punctuation key is unavailable in the active keyboard layout")
            code = mapped & 0xFF
            shift = (mapped >> 8) & 0xFF
            flags |= (4 if shift & 1 else 0) | (2 if shift & 2 else 0) | (1 if shift & 4 else 0)
    else:
        raise ValueError("Use a modified letter/digit/punctuation key or F1–F24")
    return flags, code


class GlobalHotkeys:
    def __init__(self, bindings, activate, report, ready=None):
        self.bindings, self.activate, self.report = bindings, activate, report
        self.ready = ready
        self.ready_event = threading.Event()
        self.thread_id = None
        self.registered_count = 0
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="global-hotkeys", daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=2)

    def _run(self):
        if sys.platform != "win32":
            self.report("Global hotkeys require Windows; use app-focused shortcuts here.")
            return
        api = ctypes.windll.user32
        self.thread_id = threading.get_native_id()
        message = wintypes.MSG()
        # Ensure this worker owns a Win32 message queue before registration.
        api.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        registered = []
        try:
            for ident, (action, sequence) in enumerate(self.bindings.items(), 1):
                if not sequence:
                    continue
                modifiers, key = parse_hotkey(sequence)
                if api.RegisterHotKey(None, ident, modifiers | 0x4000, key):  # MOD_NOREPEAT
                    registered.append(ident)
                else:
                    self.report(f"Hotkey {sequence} is unavailable; change its binding.")
            self.registered_count = len(registered)
            self.ready_event.set()
            if self.ready:
                self.ready(len(registered), sum(bool(key) for key in self.bindings.values()))
            actions = list(self.bindings)
            while not self.stop_event.wait(.03):
                while api.PeekMessageW(ctypes.byref(message), None, 0x0312, 0x0312, 1):
                    ident = int(message.wParam)
                    if ident in registered:
                        self.activate(actions[ident - 1])
        finally:
            self.ready_event.set()
            for ident in registered:
                api.UnregisterHotKey(None, ident)
