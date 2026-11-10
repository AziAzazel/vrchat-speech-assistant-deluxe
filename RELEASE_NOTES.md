VRChat Speech Assistant Deluxe 1.17.0 release candidate 1

Download VRChatSpeechAssistantDeluxe.exe (Windows x64). Replace the old executable;
existing settings remain in %APPDATA%/VRChat Speech Assistant.

New features:
- Pronunciation dictionary under Edit: displayed word → spoken respelling,
  applied after translation to synthesis only. Chatbox spelling is unchanged.
  Saved separately from nickname corrections in pronunciation.json.
- Session history from File or the message section: last 50 attempts with source,
  result, pronunciation and completion/cancellation/failure status. Memory only;
  nothing is saved to disk or diagnostic logs. Clearable, empty after restart.
- Load a history source for editing, or repeat its result with the current voice
  without retranslation or another random ending. Unsent drafts are protected.
- Collapse whole UI sections by their headers. States are remembered; recognition
  preview opens the message section when needed. Voice, Chatbox and Random ending
  start collapsed.
- Random ending text such as ", poi" or ", desu", with a 0–100% frequency slider:
  0% never, 100% always. Applies once after translation to speech and chatbox,
  before final punctuation, with settings saved. Off by default.

All prior functionality remains: global hotkeys, per-language/provider voices,
saved pitch/window size, responsive columns, delayed editable preview, stop
speech, audio recovery, local Windows speech, optional Polly and external Piper.

The executable is unsigned. CI verifies the packaged GUI, native hotkey dispatch,
SAPI WAV generation, pronunciation formatting, history UI, category collapse and
ending controls. Live audio/VRChat routing still needs user hardware testing.
