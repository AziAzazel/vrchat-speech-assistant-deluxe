"""Local, duration-preserving pitch processing shared by every speech backend."""
from contextlib import contextmanager
from pathlib import Path
import tempfile

from vrchat_speech_assistant.output_control import check_cancelled

MIN_PITCH, MAX_PITCH = -75, 300


def validate_pitch(value):
    if type(value) is not int or not MIN_PITCH <= value <= MAX_PITCH:
        raise ValueError('Pitch must be a whole percentage between -75 and +300.')
    return value


def shift_pitch(samples, percent):
    """Band-limited resampling followed by phase-vocoder time restoration.

    Input/output are frames × channels. Each channel retains its frame count;
    neither the playback sample rate nor the selected delivery rate is changed.
    """
    import numpy as np
    validate_pitch(percent)
    check_cancelled()
    if not percent or not len(samples):
        return samples.copy()
    count, channels = samples.shape
    factor = 1 + percent / 100
    size = max(1, round(count / factor))
    # Fourier resampling removes frequencies above the new Nyquist limit.
    spectrum = np.fft.rfft(samples, axis=0)
    resampled_spectrum = np.zeros((size // 2 + 1, channels), dtype=complex)
    shared = min(count, size)
    resampled_spectrum[:shared // 2 + 1] = spectrum[:shared // 2 + 1]
    if shared % 2 == 0:
        if size < count:
            resampled_spectrum[shared // 2] *= 2
        elif count < size:
            resampled_spectrum[shared // 2] *= .5
    resampled = np.fft.irfft(resampled_spectrum, n=size, axis=0) * (size / count)
    check_cancelled()
    fft_size, hop = 2048, 512
    window = np.hanning(fft_size)
    padded = np.pad(resampled, ((fft_size // 2, fft_size), (0, 0)))
    output = np.zeros((count + fft_size * 2, channels))
    weights = np.zeros(len(output))
    advance = 2 * np.pi * hop * np.arange(fft_size // 2 + 1)[:, None] / fft_size
    phase = None
    previous_index = None
    for frame, position in enumerate(np.arange(0, size / hop, size / count)):
        if frame % 32 == 0:
            check_cancelled()
        index = int(position)
        if previous_index != index:
            first = np.fft.rfft(padded[index * hop:index * hop + fft_size] * window[:, None], axis=0)
            second = np.fft.rfft(padded[(index + 1) * hop:(index + 1) * hop + fft_size] * window[:, None], axis=0)
            previous_index = index
        if phase is None:
            phase = np.angle(first)
        fraction = position - index
        magnitude = (1 - fraction) * np.abs(first) + fraction * np.abs(second)
        block = np.fft.irfft(magnitude * np.exp(1j * phase), n=fft_size, axis=0)
        offset = frame * hop
        output[offset:offset + fft_size] += block * window[:, None]
        weights[offset:offset + fft_size] += window ** 2
        delta = np.angle(second) - np.angle(first) - advance
        delta -= 2 * np.pi * np.round(delta / (2 * np.pi))
        phase += advance + delta
    output /= np.maximum(weights[:, None], 1e-10)
    result = output[fft_size // 2:fft_size // 2 + count]
    # Avoid hard clipping if overlap/add introduces a transient overshoot.
    peak = np.max(np.abs(result))
    if peak > 1:
        result /= peak
    check_cancelled()
    return result.astype(np.float32)


@contextmanager
def pitched_audio(path, tags=None):
    """Keep originals intact; playback and history receive the same final WAV."""
    percent = validate_pitch((tags or {}).get('pitch', 0))
    if not percent:
        yield Path(path)
        return
    import soundfile as sf
    check_cancelled()
    samples, rate = sf.read(str(path), dtype='float32', always_2d=True)
    shifted = shift_pitch(samples, percent)
    with tempfile.TemporaryDirectory(prefix='deluxe-pitch-') as directory:
        target = Path(directory) / 'speech.wav'
        sf.write(str(target), shifted, rate, subtype='PCM_16')
        check_cancelled()
        yield target
