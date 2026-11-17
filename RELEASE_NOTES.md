# VRChat Speech Assistant Deluxe 1.32.0rc1

Local pitch now works with Windows Speech, Piper and Amazon Polly, including Neural voices. The −75% to +300% range covers two octaves down/up without changing tempo. Audio export includes the effect you hear.

Polly receives no SSML pitch. Whisper is offered only for supported Standard voices in the main controls, Roleplay and Soundboard; incompatible selections reset to Normal. Changing pitch reuses dry Polly audio instead of requesting another synthesis.

Windows x64 and Linux x86-64 assets are published together only after their tests and packaged GUI/audio smoke checks pass. Microphone recognition, physical VRChat routing and live AWS/DeepL credentials still need verification on the user's hardware/account.
