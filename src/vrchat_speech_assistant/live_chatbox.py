"""Immediate chatbox pages advanced during a single synthesized utterance."""
from bisect import bisect_right
import time

from vrchat_speech_assistant.output_control import check_cancelled, cancellation_event, OutputCancelled

MAX_UNITS = 144
MIN_INTERVAL = 1.5


def utf16_units(text):
    return len(text.encode('utf-16-le')) // 2


def split_pages(text, limit=MAX_UNITS):
    """Split on word boundaries where possible, including long words/CJK/emoji."""
    pages = []
    remaining = text.strip()
    while remaining:
        units, end = 0, 0
        for index, character in enumerate(remaining):
            size = 2 if ord(character) > 0xFFFF else 1
            if units + size > limit:
                break
            units += size
            end = index + 1
        if not end:
            raise ValueError('Chatbox page limit is too small for this character.')
        if end < len(remaining):
            boundary = next((index for index in range(end, 0, -1) if remaining[index-1].isspace()), 0)
            if boundary and remaining[:boundary].strip():
                end = boundary
        page = remaining[:end].strip()
        if page:
            pages.append(page)
        remaining = remaining[end:].lstrip()
    return pages


def wait_until(deadline):
    while True:
        check_cancelled()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        event = cancellation_event()
        if event is not None:
            event.wait(min(remaining, .05))
        else:
            time.sleep(min(remaining, .05))


class ChatboxOutputError(Exception):
    """Classify OSC failures separately from audio failures without message text."""


class LiveChatbox:
    def __init__(self, text, send, spoken_text='', clock=time.monotonic, wait=wait_until):
        self.pages = split_pages(text)
        self.send = send
        self.clock, self.wait = clock, wait
        self.index = -1
        self.last_sent = float('-inf')
        weights = [max(1, len(page)) for page in self.pages]
        total = sum(weights) or 1
        self.starts = []
        cumulative = 0
        for weight in weights:
            self.starts.append(cumulative/total)
            cumulative += weight
        self.estimated_duration = max(MIN_INTERVAL, len(spoken_text or text)/14)
        self.had_playback = False

    def _send_next(self):
        check_cancelled()
        try:
            self.send(self.pages[self.index+1])
        except OutputCancelled:
            raise
        except Exception as error:
            raise ChatboxOutputError() from error
        self.index += 1
        self.last_sent = self.clock()

    def start(self):
        if self.pages:
            self._send_next()

    def progress(self, position, duration):
        """Use the audio clock; page boundaries are proportional, not word marks."""
        check_cancelled()
        self.had_playback = True
        duration = duration if duration and duration > 0 else self.estimated_duration
        desired = min(len(self.pages)-1, bisect_right(self.starts, max(0, position)/duration)-1)
        if self.index < desired and self.clock()-self.last_sent >= MIN_INTERVAL:
            # Never skip an unseen page, even after a slow frame.
            self._send_next()

    def finish(self, with_speech=False):
        """Keep all pages readable if audio is unavailable/very short or text-only."""
        while self.index+1 < len(self.pages):
            hold = MIN_INTERVAL if with_speech and self.had_playback else max(2.0, len(self.pages[self.index])/18)
            self.wait(self.last_sent + hold)
            self._send_next()
