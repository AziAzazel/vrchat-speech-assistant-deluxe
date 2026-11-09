VRChat Speech Assistant Deluxe 1.15.0 release candidate 1

Download **VRChatSpeechAssistantDeluxe.exe** below. It is a standalone Windows
x64 application; Windows speech and Polly need no separate Python installation.

New features:
- Local Windows speech as the default provider, with optional online Polly fallback.
- Pasted-text speech for manual ChatGPT responses.
- Nickname corrections and keyword-triggered chatbox text/emoji additions.
- Personality presets, editable announcements, hotkeys and delivery modes.
- Rotating crash diagnostics and safer speech/thread handling.

Getting started:
1. Run the executable and choose your microphone and speech output device.
2. Select an installed Windows desktop voice under Show Speech settings.
3. Choose your virtual cable as output for VRChat; enable OSC for chatbox output.
4. Configure your own DeepL/AWS credentials only if using those services.
5. Roleplay settings include global hotkeys; enable them to use shortcuts while VRChat is focused.

Notes:
- This first public Deluxe build is a release candidate. CI verifies packaged GUI
  startup and real SAPI WAV generation; live microphone/virtual cable/VRChat use
  still needs testing on user hardware.
- Genuine whisper is supported through Polly; local providers support pacing
  and the deliberate malfunction stutter.
- Piper is optional and external to this executable. Install Piper separately,
  then choose its piper.exe backend and downloaded voice model in Speech settings.
- Speech recognition still uses Google; this is not a fully offline application.
- Standard OSC chatbox input cannot embed images.
- The executable is unsigned. No code-signing certificate was supplied.
- Logs: %APPDATA%/VRChat Speech Assistant/logs. No shared API keys are bundled.
