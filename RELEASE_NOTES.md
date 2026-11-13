VRChat Speech Assistant Deluxe 1.27.0 release candidate 1

First native Linux x86-64 preview, sharing the Windows code and version.

Downloads:
- Windows: VRChatSpeechAssistantDeluxe.exe
- Linux/Bazzite Desktop Mode: VRChatSpeechAssistantDeluxe-1.27.0rc1-linux-x86_64.tar.gz
  Extract the entire folder and run start.sh. Keep _internal beside the executable.
  No Python install or system-image changes are required. Targets glibc 2.35+.

Read docs/LINUX.md (also LINUX.md inside the archive) for setup and current limits.
Linux defaults to external Piper; select its Linux executable and .onnx/.onnx.json
voice assets, or choose Amazon Polly and your own AWS credentials. Windows Speech
is Windows-only. Existing Soundboard Windows voice entries must be edited.

Edit → Linux audio routing / virtual microphone creates a user-session output and
microphone with pactl. Select VRChat_Speech_Deluxe as speech output and
VRChat_Speech_Deluxe_Microphone in VRChat. Keep recognition on your real microphone;
use pavucontrol/qpwgraph for per-stream routing. System defaults stay unchanged.
The route may be restored on startup; closing the app leaves it in place.

Shared features include recognition/manual input, DeepL translation, Polly pitch
and whisper, Soundboard/favorite reactions, separate chatbox text, preview/history,
pronunciation, random endings, WAV/MP3 and SRT.

Linux limits: in-app hotkeys need focus; use --action with KDE custom shortcuts for
Desktop Mode global actions. Gaming Mode/controller overlays are not validated.
The owned YouTube/Edge player remains Windows-only. Route a Linux browser manually;
Deluxe Stop cannot stop that external browser.

Both Windows and Linux build checks must pass before publishing this release.
Linux checks include real packaged GUI, isolated audio enumeration, a real sine
wave captured through the virtual microphone and actual OSC UDP delivery. Physical
Legion/Bazzite hardware, VRChat reception, real Google recognition and credentials
still require testing on the user's machine. This is the first Linux preview.
