VRChat Speech Assistant Deluxe 1.25.0 release candidate 1

Add a saved Pitch control to Roleplay → Soundboard phrases and hotkeys.
- Range: -50% to +50%, with 0% for the natural voice pitch.
- Each phrase saves its own pitch; the main Voice pitch slider is unchanged.
- Combine pitch with Whispered delivery on a Polly Standard voice such as Mizuki.
- Nonzero pitch requires Polly Standard. Windows/Piper and Polly Neural voices
  require pitch 0; unsupported spoken combinations are rejected before output.
- Old phrases default to pitch 0. Chatbox-only rows retain the value without
  applying it, and recordings keep their original audio/SRT behavior.
- Widen the Soundboard window to accommodate the additional control.

Example: Ctrl+; | Speech: ぽい | Chatbox: 👀 | Japanese | Voice + chatbox |
Amazon Polly | Mizuki | Whispered | Pitch: +20%.

Download VRChatSpeechAssistantDeluxe.exe (Windows x64) and replace the old file.
Existing settings survive. Validation covers -50/0/+50 across all output routes,
invalid values and unsupported providers, saved/reopened controls, and packaged
Windows GUI checks. No live Polly request is made by the automated tests;
actual voice quality and VRChat reception require configured user hardware/services.
