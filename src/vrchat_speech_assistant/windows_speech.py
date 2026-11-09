"""Local Windows SAPI voices, rendered to WAV for selected-device playback."""
import contextlib
import tempfile
from pathlib import Path


class LocalSynthesisError(RuntimeError):
    """Local synthesis failed before playback began."""


@contextlib.contextmanager
def sapi():
    # COM objects must be created and released in the thread using them.
    import pythoncom
    from win32com.client import Dispatch
    pythoncom.CoInitialize()
    try:
        yield Dispatch
    finally:
        pythoncom.CoUninitialize()


class WindowsSpeech:
    """Use installed desktop SAPI voices without any online credentials."""

    def __init__(self):
        with sapi() as dispatch:
            voice = dispatch("SAPI.SpVoice")
            self.voices = {token.GetDescription(): token.Id for token in voice.GetVoices()}
            del voice

    def render(self, text, voice_name, path, rate=100):
        try:
            with sapi() as dispatch:
                voice = dispatch("SAPI.SpVoice")
                token = dispatch("SAPI.SpObjectToken")
                token.SetId(self.voices[voice_name])
                voice.Voice = token
                voice.Rate = max(-10, min(10, round((rate - 100) / 10)))
                stream = dispatch("SAPI.SpFileStream")
                try:
                    stream.Open(str(path), 3, False)  # SSFMCreateForWrite
                    voice.AudioOutputStream = stream
                    voice.Speak(text, 16)  # SVSFIsNotXML: pasted text is literal.
                finally:
                    stream.Close()
                    del stream, token, voice
        except Exception as error:
            raise LocalSynthesisError("Windows speech synthesis failed") from error

    def speech(self, text, voice_id, output_device_name, extra_tags=None):
        from vrchat_speech_assistant.providers import read_ogg_file
        with tempfile.TemporaryDirectory(prefix="vrcspeech-") as directory:
            path = Path(directory) / "speech.wav"
            if extra_tags and extra_tags.get("rate"):
                self.render(text, voice_id, path, rate=extra_tags["rate"])
            else:
                self.render(text, voice_id, path)
            # Playback failure is deliberately not a synthesis failure: never replay
            # a partially heard utterance through an online fallback.
            read_ogg_file(str(path), output_device_name)


class UnavailableWindowsSpeech:
    voices = {}

    def speech(self, *args):
        raise LocalSynthesisError("No Windows desktop speech voice is available")


class SpeechWithFallback:
    """Contact Polly only after local synthesis fails and fallback was enabled."""

    def __init__(self, primary, fallback_factory, fallback_voice, notify):
        self.primary = primary
        self.fallback_factory = fallback_factory
        self.fallback_voice = fallback_voice
        self.notify = notify

    def speech(self, text, voice_id, output_device_name, extra_tags=None):
        try:
            self.primary.speech(text, voice_id, output_device_name, extra_tags)
        except LocalSynthesisError:
            if self.fallback_voice == "None":
                raise
            self.notify()
            provider = self.fallback_factory()
            provider.speech(text, self.fallback_voice, output_device_name, extra_tags)
