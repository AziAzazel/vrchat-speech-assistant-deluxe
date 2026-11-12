"""Providers classes that can be used as speech_provider attribute for the VRCSpeechAssistant class."""

import contextlib
import hashlib
import json
import time
from xml.sax.saxutils import escape

from vrchat_speech_assistant.diagnostics import DATA_DIR
from vrchat_speech_assistant.output_control import check_cancelled, playback_callback
from vrchat_speech_assistant.languages import POLLY_VOICES_ENGINE

VOICES_PATH = DATA_DIR / "voices"




class UnsupportedSpeechStyle(ValueError):
    """Safe, actionable capability message with no submitted text or credentials."""


def polly_engine(voice):
    return POLLY_VOICES_ENGINE.get(voice.split(" ", 1)[0], "standard")


def validate_polly_style(voice, tags):
    if polly_engine(voice) == "neural" and (tags.get("whispered") or tags.get("pitch")):
        raise UnsupportedSpeechStyle(
            "This Neural voice does not support whisper or pitch. Set pitch to 0, tags to None "
            "and delivery to Normal/Measured/Warning, or choose a Standard voice.")


class Polly:
    """Use Amazon Polly API to synthesize a speech.

    This class can be used as speech_provider attribute for the VRCSpeechAssistant class.

    Parameters
    ----------
    aws_access_key_id : str
        The AWS access key ID used to authenticate with the Amazon Polly API.
    aws_secret_access_key : str
        The AWS secret access key used to authenticate with the Amazon Polly API.
    region_name : str
        The region name where the Amazon Polly service is located.
    """

    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region_name: str):
        import boto3
        from botocore.config import Config
        my_config = Config(region_name=region_name, connect_timeout=10, read_timeout=30, retries={"max_attempts": 1})
        self.client = boto3.client(
            "polly",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=my_config,
        )

    def speech(self, text: str, voice_id: str, output_device_name: str, extra_tags: dict = None):
        """Convert a text into a speech and then play it to the given output_device.

        Parameters
        ----------
        text : str
            The text to be converted to speech.
        voice_id : str
            The voice id of the voice you want to use.
        output_device_name : str
            The output device name.
        extra_tags : dict
            A dict of extra tags.
        """

        engine = polly_engine(voice_id)
        validate_polly_style(voice_id, extra_tags or {})
        def convert_to_ssml(input_text):
            # https://docs.aws.amazon.com/polly/latest/dg/supportedtags.html
            ssml_tags = escape(input_text)
            if engine == "standard":
                ssml_tags = '<amazon:auto-breaths frequency="low" volume="soft" duration="x-short">' + ssml_tags + "</amazon:auto-breaths>"
            if extra_tags:
                if extra_tags.get("whispered", False) is True:
                    ssml_tags = f'<amazon:effect name="whispered">{ssml_tags}</amazon:effect>'
                if extra_tags.get("rate"):
                    ssml_tags = '<prosody rate="{}%">{}</prosody>'.format(extra_tags["rate"], ssml_tags)
                if extra_tags.get("pitch"):
                    ssml_tags = '<prosody pitch="{}%">{}</prosody>'.format(extra_tags["pitch"], ssml_tags)
            return f"<speak>{ssml_tags}</speak>"

        # Hash content/settings to avoid long filenames, collisions and transcript leaks.
        cache_key = [text, extra_tags] if engine == "standard" else [text, extra_tags, engine]
        filename = hashlib.sha256(json.dumps(cache_key, sort_keys=True).encode()).hexdigest()
        filepath = VOICES_PATH / voice_id / f"{filename}.ogg"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # Create the answer from Amazon Polly if the file does not exist
        if not filepath.exists():
            response = self.client.synthesize_speech(
                Engine=engine,
                Text=convert_to_ssml(text),
                VoiceId=voice_id.split(" ")[0],
                OutputFormat="ogg_vorbis",
                TextType="ssml",
            )
            temporary = filepath.with_suffix(".tmp")
            with contextlib.closing(response["AudioStream"]) as stream:
                temporary.write_bytes(stream.read())
            temporary.replace(filepath)
        read_ogg_file(str(filepath), output_device_name)

    def test(self) -> bool:
        """Test Amazon Polly credentials.

        Returns
        -------
        bool
            The test result.
        """
        from botocore.exceptions import ClientError
        with contextlib.suppress(ClientError):
            response = self.client.synthesize_speech(Text="test", VoiceId="Justin", OutputFormat="ogg_vorbis")
            with contextlib.closing(response["AudioStream"]):
                return True
        return False


def read_ogg_file(filepath: str, output_device_name: str):
    """Reads an .ogg audio file and plays it using a specified output device.

    Parameters
    ----------
    filepath : str
        The path to the .ogg audio file.
    output_device_name : str
        The name of the output device to use for audio playback.
    """

    import pygame
    import pygame.mixer
    check_cancelled()
    pygame.mixer.pre_init(devicename=output_device_name)
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(filepath)
        callback = playback_callback()
        duration = None
        if callback is not None:
            try:
                import wave
                with wave.open(str(filepath), 'rb') as audio:
                    duration = audio.getnframes()/audio.getframerate()
            except (wave.Error, EOFError, OSError, ZeroDivisionError):
                try:
                    sound = pygame.mixer.Sound(filepath)
                    duration = sound.get_length()
                    del sound
                except pygame.error:
                    pass  # Caption controller falls back to a reading-time estimate.
        pygame.mixer.music.play()
        if callback is not None:
            callback(0, duration)
        while pygame.mixer.music.get_busy():
            check_cancelled()
            if callback is not None:
                callback(max(0, pygame.mixer.music.get_pos()/1000), duration)
            time.sleep(0.02)
    finally:
        pygame.mixer.quit()


class PollyPool:
    """Reuse one thread-safe boto client and successful credential validation.

    Changing credentials or region replaces the cache; no keys are logged.
    """
    def __init__(self, factory=Polly):
        import threading
        self._factory = factory
        self._lock = threading.Lock()
        self._credentials = None
        self._provider = None
        self._validated = False

    def get(self, credentials, validate=False):
        access, secret, _ = credentials
        if not access or not secret:
            raise ValueError('Configure AWS credentials for Amazon Polly.')
        with self._lock:
            if self._credentials != credentials:
                provider = self._factory(*credentials)
                self._provider = provider
                self._credentials = credentials
                self._validated = False
            if validate and not self._validated:
                if not self._provider.test():
                    raise ValueError('Amazon Polly credentials could not be validated.')
                self._validated = True
            return self._provider
