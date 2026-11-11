VRChat Speech Assistant Deluxe 1.18.0 release candidate 2

Fix for the reported Windows fatal exception / access violation when starting
microphone capture while the automatic audio device scan is running.

- Enumerate devices in a separate helper process, avoiding concurrent PortAudio
  initialization/termination in the capture process.
- A crashed or hung scanner cannot take down the GUI through shared PortAudio
  state. Failed scans preserve the previous device list and listener state and
  retry on the next refresh. Actual disconnect/reconnect handling is retained.
- Bound helper execution to 30 seconds, suppress helper windows/error dialogs,
  and record numeric exit codes without device names, transcripts or keys.
- Regression checks cover the real subprocess boundary, abrupt helper exit,
  invalid reports, timeout handling and preserving capture after a failed scan.
  Packaged Windows tests scan twice while the parent holds a PortAudio context.

Download VRChatSpeechAssistantDeluxe.exe (Windows x64) and replace the old file.
Existing settings remain in %APPDATA%/VRChat Speech Assistant.
All previous Deluxe features and the 1.18 upstream catalogue updates remain.

The supplied crash shows an overlapping PortAudio lifecycle. The fix removes
that overlap; the exact user driver/hardware crash still needs user validation.
