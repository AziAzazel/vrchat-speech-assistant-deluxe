VRChat Speech Assistant Deluxe 1.19.0 release candidate 1

New: Roleplay → Soundboard phrases and hotkeys.
- Up to 32 saved phrases, each with shortcut, language, route, provider and voice.
- Voice only, Chatbox only, or Voice + chatbox, independent of the main toggles.
- Default example: Ctrl+; → ぽい (poi), Japanese, Voice only, Polly Mizuki.
  Uses your AWS keys; select an installed Japanese Windows voice or configured
  Japanese Piper model for local synthesis instead.
- Windows punctuation shortcuts, including Ctrl+;, follow the keyboard layout.
  Shortcut conflicts across Roleplay/Soundboard are rejected; global registration
  failures are shown. The existing global hotkey switch controls both sets.
- Add/remove/edit, Play selected preview, persistent settings and session history.
- Saved phrases bypass translation, substitutions, random endings, personality
  delivery and chatbox decorations. Main language/voice/editor text are retained.
- Text-only phrases require no audio or AWS setup. Voice-only sends no chatbox
  text/typing status. Busy output is not queued; Stop speaking cancels playback.

Download VRChatSpeechAssistantDeluxe.exe (Windows x64) and replace the old file.
Existing configuration and the 1.18.0rc2 isolated audio scanner fix are preserved.

Validation: automated route/isolation/persistence/conflict tests, plus native
Windows shortcut registration (including semicolon), packaged soundboard dialog,
SAPI synthesis and the existing application smoke tests. No live AWS requests
were made; Japanese voice quality and VRChat routing need user hardware testing.
