"""Bounded, session-only retention of final synthesized audio, including effects."""
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

MAX_AUDIO_BYTES = 32 * 1024 * 1024


class AudioRetentionError(ValueError):
    pass


@dataclass(frozen=True)
class GeneratedAudio:
    extension: str
    data: bytes


def read_generated_audio(path):
    path = Path(path)
    if path.stat().st_size > MAX_AUDIO_BYTES:
        raise AudioRetentionError('Audio exceeds the 32 MB export retention limit.')
    with path.open('rb') as source:
        data = source.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise AudioRetentionError('Audio exceeds the 32 MB export retention limit.')
    if data[:4] == b'RIFF' and data[8:12] == b'WAVE':
        extension = '.wav'
    elif data[:4] == b'OggS':
        extension = '.ogg'
    else:
        raise AudioRetentionError('No supported generated audio file was retained.')
    return GeneratedAudio(extension, data)


def save_generated_audio(clip, target):
    target = Path(target)
    if target.suffix.lower() != clip.extension:
        raise ValueError('Choose the original audio format; export does not convert WAV/OGG to MP3.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.deluxe-audio-', delete=False) as output:
            temporary = Path(output.name)
            output.write(clip.data)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
