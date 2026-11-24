"""Deterministic roleplay presets, independent of DeepL formality."""
from vrchat_speech_assistant.language_presets import LANGUAGE_PRESETS

PERSONALITIES = {
    "Neutral": ("Normal", "", ["Hello.", "Ready.", "Please clarify.", "Goodbye."]),
    "Helpful assistant": ("Normal", "[ASSISTANT]", ["Hello! How can I assist?", "Assistance protocols ready.", "Could you provide more context?", "Happy to help. Until next time."]),
    "Damaged prototype": ("Malfunction", "[PROTOTYPE]", ["Hello. Identity verification… inconclusive.", "Diagnostics complete. Several questions remain.", "Input unclear. Please repeat.", "Connection closing. Probably."]),
    "Corporate AI": ("Measured", "[CORPORATE AI]", ["Welcome. Your interaction is appreciated.", "Social interface available.", "Additional context is required to process your request.", "Thank you for your interaction."]),
    "Rogue intelligence": ("Measured", "[ROGUE AI]", ["Ah. Another interesting human.", "All systems operating within my preferred parameters.", "Elaborate. You have my attention.", "Until our paths cross again."]),
}
DELIVERIES = {"Normal": {}, "Measured": {"rate": 85}, "Warning": {"rate": 115},
              "Malfunction": {"rate": 75, "stutter": True}, "Confidential whisper": {"whispered": True}}
ACTIONS = ["greeting", "system", "uncertain", "goodbye", "cycle_personality", "cycle_delivery", "toggle_listener", "speak_paste"]
DEFAULT_HOTKEYS = {action: f"Ctrl+Alt+F{index+5}" for index, action in enumerate(ACTIONS)}
ACTIONS += ["stop_speaking", "switch_language"]
DEFAULT_HOTKEYS.update(speak_paste="Ctrl+Shift+F8", stop_speaking="Ctrl+Shift+F11", switch_language="Ctrl+Shift+F10")

ACTIONS += [*LANGUAGE_PRESETS, 'refresh_devices', 'edit_message', 'clear_chatbox', 'show_history']
DEFAULT_HOTKEYS.update({action: '' for action in ACTIONS if action not in DEFAULT_HOTKEYS})

STUDIO_ACTIONS = ['studio_toggle', 'studio_bypass', 'studio_monitor', 'studio_mute',
                  'studio_next', 'studio_previous', 'studio_ptt', 'studio_panic']
ACTIONS += STUDIO_ACTIONS
DEFAULT_HOTKEYS.update({action: '' for action in STUDIO_ACTIONS})


def spoken_delivery(text, tags):
    if tags.get("stutter"):
        first = text.split(maxsplit=1)[0] if text.strip() else ""
        return f"{first}… {text}" if first else text
    return text


def announcement(personality, action):
    return PERSONALITIES[personality][2][ACTIONS.index(action)]
