"""Top-level package for VRChat Speech Assistant."""

from vrchat_speech_assistant._version import __version__
from vrchat_speech_assistant.diagnostics import setup_logging

setup_logging()


def __getattr__(name):
    if name == "VRCSpeechAssistantWindow":
        from vrchat_speech_assistant.main import VRCSpeechAssistantWindow
        return VRCSpeechAssistantWindow
    raise AttributeError(name)

__author__ = """Amelien Deshams"""
__email__ = "a.deshams+git@slmail.me"
__all__ = [
    "VRCSpeechAssistantWindow"
]
