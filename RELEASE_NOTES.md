VRChat Speech Assistant Deluxe 1.24.0 release candidate 1

Soundboard phrases can now show different text from what they say.
- Speech / name: the phrase spoken by the saved voice.
- Chatbox text: independent text or emoji. Leave blank to show the spoken phrase,
  preserving existing shortcuts.
- Delivery: Normal or Whispered, saved separately for each phrase. Whispered
  requires an Amazon Polly Standard voice; Windows/Piper and Polly Neural voices
  do not support this effect. Unsupported combinations are rejected before output.

Example in Roleplay → Soundboard phrases and hotkeys:
Ctrl+; | Speech: ぽい | Chatbox: 👀 | Japanese | Voice + chatbox |
Amazon Polly | Mizuki | Whispered.
The eyes appear before synthesis; the voice says only ぽい. Main speech settings,
translation, corrections and random endings do not alter the phrase. The selected
application output device is used. AWS credentials are required for Polly.

Voice-only and chatbox-only routes still work. Recordings keep their SRT captions.
Existing entries need no migration: matching chatbox text and Normal delivery are
used until the new fields are edited. Settings survive replacing the executable.

Download VRChatSpeechAssistantDeluxe.exe (Windows x64) and replace the old file.
Validation covers independent speech/captions across all three routes, old presets,
saved/reopened controls and unsupported whisper combinations. Packaged Windows
smoke checks exercise the new controls without making live Polly requests.
Actual Polly whisper and VRChat reception require configured user hardware/services.
