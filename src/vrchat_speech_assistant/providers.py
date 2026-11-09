"""Providers classes that can be used as speech_provider attribute for the VRCSpeechAssistant class."""

import contextlib
import hashlib
import json
import time
from xml.sax.saxutils import escape

import boto3
import botocore
import botocore.exceptions
import pygame
import pygame.mixer
from botocore.config import Config
from vrchat_speech_assistant.diagnostics import DATA_DIR

VOICES_PATH = DATA_DIR / "voices"




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
        my_config = Config(region_name=region_name)
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

        def convert_to_ssml(input_text):
            # https://docs.aws.amazon.com/polly/latest/dg/supportedtags.html
            ssml_tags = (
                '<amazon:auto-breaths frequency="low" volume="soft" duration="x-short">'
                + escape(input_text)
                + "</amazon:auto-breaths>"
            )
            if extra_tags:
                if extra_tags.get("whispered", False) is True:
                    ssml_tags = f'<amazon:effect name="whispered">{ssml_tags}</amazon:effect>'
                if extra_tags.get("rate"):
                    ssml_tags = '<prosody rate="{}%">{}</prosody>'.format(extra_tags["rate"], ssml_tags)
                if extra_tags.get("pitch"):
                    ssml_tags = '<prosody pitch="{}%">{}</prosody>'.format(extra_tags["pitch"], ssml_tags)
            return f"<speak>{ssml_tags}</speak>"

        # Hash content/settings to avoid long filenames, collisions and transcript leaks.
        filename = hashlib.sha256(json.dumps([text, extra_tags], sort_keys=True).encode()).hexdigest()
        filepath = VOICES_PATH / voice_id / f"{filename}.ogg"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # Create the answer from Amazon Polly if the file does not exist
        if not filepath.exists():
            try:
                response = self.client.synthesize_speech(
                    Text=convert_to_ssml(text),
                    VoiceId=voice_id.split(" ")[0],
                    OutputFormat="ogg_vorbis",
                    TextType="ssml",
                )
                temporary = filepath.with_suffix(".tmp")
                with contextlib.closing(response["AudioStream"]) as stream:
                    temporary.write_bytes(stream.read())
                temporary.replace(filepath)
            except botocore.exceptions.ClientError:
                raise
        read_ogg_file(str(filepath), output_device_name)

    def test(self) -> bool:
        """Test Amazon Polly credentials.

        Returns
        -------
        bool
            The test result.
        """
        with contextlib.suppress(botocore.exceptions.ClientError):
            self.client.synthesize_speech(Text="test", VoiceId="Justin", OutputFormat="ogg_vorbis")
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

    pygame.mixer.pre_init(devicename=output_device_name)
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.02)
    finally:
        pygame.mixer.quit()
