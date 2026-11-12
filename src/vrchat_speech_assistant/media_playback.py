"""Cancellable file playback and SRT captions driven by the audio clock."""
from dataclasses import dataclass
import html
from pathlib import Path
import re
import time

from vrchat_speech_assistant.output_control import check_cancelled

CAPTION_INTERVAL = 1.5
_TIMESTAMP = r'(\d{1,3}):([0-5]\d):([0-5]\d)[,.](\d{3})'
_TIMING = re.compile(r'^' + _TIMESTAMP + r'\s*-->\s*' + _TIMESTAMP + r'(?:\s+.*)?$')


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def parse_srt(text):
    cues = []
    for block in re.split(r'\n\s*\n', text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n').strip()):
        lines = block.splitlines()
        if not lines:
            continue
        if lines[0].strip().isdigit():
            lines = lines[1:]
        match = _TIMING.match(lines[0].strip()) if lines else None
        if not match or len(lines) < 2:
            raise ValueError('Invalid SRT block: expected timestamps and subtitle text.')
        values = [int(value) for value in match.groups()]
        def seconds(parts):
            h, m, s, ms = parts
            return h*3600 + m*60 + s + ms/1000
        start, end = seconds(values[:4]), seconds(values[4:])
        if end <= start:
            raise ValueError('SRT subtitle end must follow its start.')
        content = html.unescape(re.sub(r'</?(?:b|i|u|font)\b[^>]*>', '', ' '.join(lines[1:]), flags=re.IGNORECASE))
        content = ' '.join(content.split())
        if content:
            cues.append(Cue(start, end, content))
    if not cues:
        raise ValueError('The SRT file contains no subtitles.')
    return sorted(cues, key=lambda cue: (cue.start, cue.end))


def load_srt(path):
    with Path(path).open('rb') as source:
        raw = source.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError('Use an SRT file smaller than 2 MB.')
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = raw.decode('utf-16')
    else:
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('cp1250')
    return parse_srt(text)


def caption_at(cues, position):
    # Multiple overlapping cues share one chatbox update.
    text = ' '.join(cue.text for cue in cues if cue.start <= position < cue.end)
    return text if len(text) <= 144 else text[:143] + '…'


class CaptionTimeline:
    """Advance through cue boundaries instead of rescanning every cue at 50 Hz."""
    def __init__(self, cues):
        self.cues = tuple(cues)
        self.events = sorted([(cue.start, 1, index) for index, cue in enumerate(self.cues)] +
                             [(cue.end, 0, index) for index, cue in enumerate(self.cues)])
        self._cursor = 0
        self._active = set()
        self._position = float('-inf')
        self._text = ''

    def at(self, position):
        changed = False
        if position < self._position:
            self._cursor = 0
            self._active.clear()
            changed = True
        self._position = position
        while self._cursor < len(self.events) and self.events[self._cursor][0] <= position:
            _, starting, index = self.events[self._cursor]
            if starting:
                self._active.add(index)
            else:
                self._active.discard(index)
            self._cursor += 1
            changed = True
        if changed:
            # Match caption_at's cue order, including overlapping captions.
            chunks, size = [], 0
            for index in sorted(self._active):
                chunks.append(self.cues[index].text)
                size += len(self.cues[index].text) + 1
                if size > 145:
                    break
            text = ' '.join(chunks)
            self._text = text if len(text) <= 144 else text[:143] + '…'
        return self._text


class CaptionSender:
    def __init__(self, client):
        self.client = client
        self.last_text = ''
        self.last_sent = float('-inf')

    def update(self, text, now):
        if text != self.last_text and now - self.last_sent >= CAPTION_INTERVAL:
            check_cancelled()
            self.client.send_message('/chatbox/input', [text, True, False])
            self.last_text, self.last_sent = text, now

    def clear(self):
        if self.last_text:
            # Cleanup is best effort, including after cancellation. Do not retain
            # a cancelled event's text or queue any future subtitle.
            try:
                self.client.send_message('/chatbox/input', ['', True, False])
            except OSError:
                pass
            self.last_text = ''


class MediaSpeech:
    def __init__(self, audio, subtitle='', offset_ms=0, output='Voice + chatbox', client=None, cues=None):
        self.audio, self.subtitle = Path(audio), subtitle
        self.offset = offset_ms/1000
        self.play_audio = output != 'Chatbox only'
        self.captions = output != 'Voice only' and bool(subtitle)
        self.client = client
        self._cues = tuple(cues) if cues is not None else None

    def speech(self, text, voice, device, tags=None):
        import pygame.mixer
        cues = (self._cues if self._cues is not None else load_srt(self.subtitle)) if self.captions else []
        sender = CaptionSender(self.client) if self.captions else None
        timeline = CaptionTimeline(cues) if sender else None
        initialized = False
        try:
            check_cancelled()
            if self.play_audio:
                pygame.mixer.pre_init(devicename=device)
                pygame.mixer.init()
                initialized = True
                pygame.mixer.music.load(str(self.audio))
                pygame.mixer.music.play()
            started = time.monotonic()
            end = max((cue.end for cue in cues), default=0) + self.offset
            while True:
                check_cancelled()
                now = time.monotonic()
                if self.play_audio:
                    if not pygame.mixer.music.get_busy():
                        break
                    position = pygame.mixer.music.get_pos()/1000
                    if position < 0:
                        position = now - started
                else:
                    position = now - started
                    if position >= end:
                        break
                if sender:
                    sender.update(timeline.at(position - self.offset), now)
                time.sleep(.02)
        finally:
            if initialized:
                pygame.mixer.quit()
            if sender:
                sender.clear()
