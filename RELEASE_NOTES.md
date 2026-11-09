VRChat Speech Assistant Deluxe 1.16.0 release candidate 2

Download **VRChatSpeechAssistantDeluxe.exe** below (Windows x64, no Python needed
for Windows speech/Polly). Replace your old executable; existing settings remain
in %APPDATA%/VRChat Speech Assistant.

New live-conversation controls:
- **Ctrl+Shift+F11:** stop speaking and cancel pending auto-send, with a matching button.
  Playback stops promptly; in-flight cloud requests may finish but their output
  is discarded. Piper generation can be interrupted. Already-sent chatbox text
  is not erased. Busy state clears after worker cleanup.
- **Transcript preview:** recognized speech appears in the manual text editor.
  A configurable 0–60 second delay controls auto-send (default 3 seconds).
  Click Edit or type to pause indefinitely, then use Speak / send now. New
  recognition never overwrites an unsent draft. Clear the editor to resume
  recognition after cancelling a draft. Disable preview for immediate output.
- **Ctrl+Shift+F12:** switch between Polish and English for recognition AND output,
  avoiding translation when speaking the same language. Configure another pair
  in Roleplay settings. Voice choices and Piper model selections are remembered
  by target language. Install/select a matching voice/model where necessary.
  Pending drafts pause when switching language.
- **Audio recovery:** devices refresh every 5 seconds or via Refresh audio devices.
  Microphone capture failures are logged, and requested listening resumes when
  the selected microphone reconnects. Cancel listening to disable recovery.
  Missing outputs are retained, never silently routed to another device; after
  reconnecting, submit the failed message again.

Hotkeys are editable under Roleplay → Personality, delivery and hotkeys. Enable
Global Windows hotkeys there to use them while VRChat is focused.

All prior features remain: optional Polly fallback, external Piper backend,
DeepL translation, pasted text speech, nickname corrections, chatbox keyword
additions, personality presets and diagnostic logs.

CI checks the packaged GUI, real synchronous/asynchronous Windows SAPI WAV
synthesis, preview controls and language switching. Actual microphone/virtual
cable reconnects and VRChat use still need user hardware testing, so this is a
release candidate. Google recognition remains online; Piper requires its own
backend and voice assets. The executable remains unsigned.
