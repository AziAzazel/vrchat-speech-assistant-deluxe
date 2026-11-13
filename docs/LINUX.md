# Linux / Bazzite — first release candidate

[README](../README.md) · [User guide](USAGE.md) · [Changelog](../CHANGELOG.md)

Native Linux x86-64, sharing the same code/version as Windows. Start in Bazzite's
**Desktop Mode**. VRChat itself runs separately through Steam/Proton. This package
does not install or modify VRChat, Proton, system packages or the system image.
The portable build targets glibc 2.35+ (Ubuntu 22.04+, current Bazzite).

## Download and start

1. Download `VRChatSpeechAssistantDeluxe-<version>-linux-x86_64.tar.gz` from the
   same GitHub release as the Windows executable. Verify `SHA256SUMS-linux.txt`.
2. Extract the **entire** folder to a permanent location in your home directory.
   Keep the executable and `_internal` together. Do not run from inside the archive.
3. Run `start.sh` (choose Execute in the file manager), or open a terminal there
   and run `./start.sh`. No Python/pip install is needed for the portable download.
4. Optional: `./start.sh --install-desktop` adds a user menu launcher pointing to
   this folder. Moving the folder later requires running this command again.

Linux needs its normal desktop/audio libraries (ALSA, libpulse, XWayland) and a
running PipeWire-Pulse or PulseAudio user server. Bazzite normally supplies these.
`pactl` is needed only for the built-in virtual microphone helper. If missing,
install your distribution's PulseAudio utilities; do not run Deluxe as root.
The app uses Qt's X11 backend through XWayland by default.

## Voices

- **Amazon Polly:** enter your own AWS credentials. Standard voices retain pitch
  and whisper; Neural limitations are the same as Windows. DeepL is optional and
  only used for translation. Recognition still uses Google's online service.
- **Piper (offline):** the default Linux provider. Install an external Linux Piper
  executable, select it with **Choose external Piper backend…**, and select your
  `.onnx` voice model with its matching `.onnx.json`. Piper and voice models are
  not included in this archive. Use a Linux executable, not `piper.exe`.
- **Windows Speech:** unavailable on Linux. Imported main Windows Speech settings
  switch to Piper; edit any saved Soundboard Windows voices to Piper or Polly.

Soundboard, favorite reactions, independent chatbox text, pitch/whisper for Polly,
manual input, transcript editing, history, pronunciation, SRT and WAV/MP3 playback
use the same application code as Windows.

## Virtual microphone for VRChat

1. Open **Edit → Linux audio routing / virtual microphone…**.
2. Choose **Create / reuse virtual microphone**. Optionally enable its startup
   checkbox. This creates only a user-session route; system defaults stay intact.
3. Refresh devices. Choose **VRChat_Speech_Deluxe** as Deluxe's Speech output.
4. Choose **VRChat_Speech_Deluxe_Microphone** as VRChat's microphone.
5. Keep the real microphone as Deluxe's recognition input. On ALSA/PulseAudio,
   the `pulse` or `default` input uses the system/default capture route. Use
   **pavucontrol → Recording** to send Deluxe's input to the real mic and VRChat's
   input to the virtual mic if either application does not list individual sources.
   qpwgraph is another option for per-stream routing.
6. Test with a short manually typed phrase first, then enable recognition.

Never make the virtual microphone Deluxe's recognition source: that can feed
synthesized speech back into recognition. Do not change the whole system's default
microphone merely to route VRChat; use its device selector or per-stream controls.

The helper needs `pactl` and the null-sink/remap-source modules supported by
PipeWire-Pulse/PulseAudio. It reuses an existing matching route, rolls back a failed
creation and removes only modules created by this process with matching IDs/args.
Routes remain after closing Deluxe, until explicitly removed or the audio session
ends. A reused route is not owned by the new process; log out to clear it, or manage
it with your audio tools. Disable startup creation if you do not want it restored.

Speech outputs are enumerated with **SDL**, matching the playback backend; capture
inputs use **PortAudio**. This avoids offering ALSA names as incompatible SDL
output identifiers. Device scans still run in an isolated helper process.

## Hotkeys and Gaming Mode

In-app shortcuts require focus on Linux. The Windows global key registration API
is not used. In KDE Desktop Mode, configure a system custom shortcut to run:

```sh
/path/to/VRChatSpeechAssistantDeluxe/start.sh --action stop_speaking
/path/to/VRChatSpeechAssistantDeluxe/start.sh --action switch_language
/path/to/VRChatSpeechAssistantDeluxe/start.sh --action soundboard_0
```

Use any existing Roleplay action name or `soundboard_0` through `soundboard_31`.
These commands send an action to an already running Deluxe on localhost UDP 7001;
they do not create a second GUI. Delivery has no acknowledgment. Keep Deluxe open.
Closing shortcut settings continues to restore app-focused bindings.

After Desktop Mode works, you can add the executable as a non-Steam application.
Gaming Mode/Gamescope global hotkeys, controller bindings and overlays have not
been validated; KDE custom shortcuts may not be active there. Large reaction
buttons remain available when the app is focused. This is not a VR overlay.

## YouTube

The owned Edge player remains Windows-only in this first Linux build. Use a normal
browser and route its playback separately with pavucontrol/qpwgraph. Deluxe's Stop
button does not control a separately opened browser. Local Soundboard recordings,
Stop and SRT remain available.

## Settings and troubleshooting

Settings and diagnostic logs are stored in
`${XDG_CONFIG_HOME:-~/.config}/VRChat Speech Assistant/`. `APPDATA`, if explicitly
set, takes precedence (also used to isolate build checks). Keep `config.ini` private
if it contains API keys. You can copy settings from Windows while the app is closed,
but audio device names and external Piper paths must be selected again.

If the GUI does not open, run `./start.sh` in a terminal to see missing desktop
library errors. If no output appears, check the user audio server and `pactl info`;
select the exact SDL output shown in Deluxe. A disconnected device is not silently
replaced. For recognition, check the `pulse` capture route in pavucontrol.

The release pipeline checks the real packaged GUI under Xvfb, an isolated real
PortAudio/SDL probe, a real sine-wave playback captured from the virtual microphone,
and OSC delivery to a local UDP receiver. This does not establish reception in
VRChat on a physical Legion, real microphone recognition or cloud credentials;
those need a test on the target machine.

## From source

Use Python 3.12 and an isolated environment. Linux development needs PortAudio
headers, ALSA/PulseAudio libraries and Qt desktop dependencies. Install
`python -m pip install -c requirements-release.txt -e ".[tests]"`, then run
`python -m vrchat_speech_assistant`. No private `_config.py` is needed.
Build with `python scripts/build_linux.py` on Linux x86-64 (PyInstaller and numpy
also required). Windows continues to use `scripts/build_windows.py`.
