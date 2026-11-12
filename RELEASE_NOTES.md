VRChat Speech Assistant Deluxe 1.21.0 release candidate 1

New: Roleplay → YouTube player (no captions).
- Paste a YouTube video link to open the normal YouTube player in a dedicated
  Microsoft Edge app window. Use YouTube's Play/Pause, seek and volume controls.
- No downloader, media extraction, exported audio file, ad bypass or OSC captions.
  This is ordinary browser streaming with normal buffering/cache. Edge must be
  installed; YouTube consent, ads, sign-in requirements and availability apply.
- Audio routing is explicit: play the video, open Windows volume mixer and choose
  the virtual cable as Microsoft Edge output. The Speech device selector does not
  change Edge output. That Windows setting may also affect other Edge windows.
- Stop YouTube, Stop speaking, closing the panel or closing Deluxe stops only the
  owned player job, including its renderer/audio processes. Ordinary Edge windows
  stay open. The player has a dedicated browser profile/cookies/cache.
- YouTube can play alongside speech/local recordings; Stop speaking stops both.
  Pause a video with the normal YouTube controls if other output should continue.

Download VRChatSpeechAssistantDeluxe.exe (Windows x64) and replace the old file.
Existing settings, Soundboard, SRT playback and shortcut fixes are preserved.

Validation: canonical URL handling, rejection of non-YouTube targets, owned
process lifecycle and failed-launch cleanup, dialog/global Stop integration, plus
packaged Windows launch/stop of actual Edge on about:blank. CI does not play a
YouTube video or validate real hardware audio routing; those need user testing.
