VRChat Speech Assistant Deluxe 1.20.0 release candidate 1

New: WAV/MP3 recordings with optional synchronized SRT captions in Soundboard.
- Add recording, choose local audio and SRT, assign a hotkey and output route.
- Offset from -10000 to +10000 ms; positive values delay subtitles.
- Audio-only, audio + chatbox, or silent subtitles-only playback.
- Captions follow audio playback position; common SRT encodings, multiline and
  overlapping cues are supported. No transcription, translation or TTS is used.
- Chatbox updates are limited to one per 1.5 s and 144 characters; faster obsolete
  cues are skipped. This is line timing, not word-by-word karaoke. Captions end
  with the recording. VRChat/audio routing latency still needs user adjustment.
- Stop speaking cancels audio and future captions and attempts to clear the last
  caption. A Stop button is also available for Soundboard previews.

Fixed: shortcut recording in Roleplay and Soundboard settings.
- A dedicated single-chord field records immediately. Backspace/Delete clears.
- Suspend our Windows global registrations and Qt shortcuts while settings are
  open, restoring on Save/Cancel/close (including nested recording dialogs).
- Existing shortcuts no longer swallow recorded keys or fire saved phrases while
  editing. Bindings reserved by another application remain reported as conflicts.

Download VRChatSpeechAssistantDeluxe.exe (Windows x64). Existing phrase presets
and settings are preserved. Recording paths are saved; audio/SRT files stay local
and must remain at those paths. No new dependencies or cloud keys are required.

Validation covers SRT parsing/offsets/rate handling, cancellation, preserved audio
routing, real Qt key events and settings suspension/restoration. Packaged Windows
checks include actual WAV/MP3 decoding with a dummy audio device, timed OSC probe
messages, shortcut recording and the previous application smoke tests. Real audio
hardware and VRChat latency require user testing.
