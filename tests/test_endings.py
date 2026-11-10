from unittest.mock import Mock
from vrchat_speech_assistant.text_tools import add_random_ending


def test_frequency_limits_are_exact():
    draw = Mock(side_effect=AssertionError("Must not draw at 0 or 100"))
    assert add_random_ending("Hello.", ", poi", 0, draw) == "Hello."
    assert add_random_ending("Hello.", ", poi", 100, draw) == "Hello, poi."
    assert add_random_ending("Hello.", "", 100, draw) == "Hello."


def test_probability_boundary_and_punctuation():
    assert add_random_ending("Hello?", ", desu", 50, lambda: .499) == "Hello, desu?"
    assert add_random_ending("Hello?", ", desu", 50, lambda: .5) == "Hello?"
    assert add_random_ending("Hello", "poi", 100) == "Hello poi"
    assert add_random_ending("Hello.", ", poi!", 100) == "Hello, poi!"
    assert add_random_ending("Hello.", "   ", 100) == "Hello."
