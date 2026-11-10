VRChat Speech Assistant Deluxe 1.16.1 release candidate 2

Download VRChatSpeechAssistantDeluxe.exe (Windows x64). Replace the old executable;
your settings remain in %APPDATA%/VRChat Speech Assistant.

Fixes:
- Global shortcuts are enabled by default and older focus-only settings migrate
  once. A main-window checkbox and registration count make their scope visible.
  Explicit later opt-outs and other custom hotkeys remain saved.
- Initialize the native Windows hotkey message queue before registering keys.
  Conflicts are reported in the UI and logs.
- Avoid Windows' reserved F12 in defaults: Ctrl+Shift+F10 switches Polish/English,
  Ctrl+Shift+F8 speaks pasted text, Ctrl+Shift+F11 stops speech. Old default F12
  combinations migrate once; other custom bindings are preserved.
- Remember the selected voice separately for every provider and target language,
  including changes through the language dropdown and the hotkey. Remember
  fallback Polly voices per target language too.
- Save voice pitch immediately and restore it at startup. Local providers still
  do not implement Polly's pitch effect.
- Responsive 1/2/3-column layout, wrapping descriptions, expanding controls and
  compact banner. Remember window size and maximized state across restarts.

The build tests packaged GUI startup, SAPI speech, preview, language switching,
native background hotkey registration/message dispatch, responsive layout and
saved pitch. Native hotkey tests do not replace live testing inside VRChat with
your overlays and keyboard utilities. This is a release candidate and unsigned.

All previous features remain, including editable delayed transcripts, cancellation,
audio-device recovery, optional Polly fallback, external Piper, translation and
roleplay controls. No Python is needed for the default Windows speech workflow.
