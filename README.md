# VRChat Speech Assistant Deluxe

[Download the Windows executable](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases)

The standalone Windows x64 download includes Windows speech, Polly, translation,
manual text speech and the roleplay controls. No Python installation is needed
for those features. Piper remains an optional external backend: install Piper
separately and select its `piper.exe` and voice assets in Speech settings.


This fork preserves the original Google recognition, DeepL translation, Amazon
Polly synthesis and VRChat OSC workflow. It adds manual text input, nickname
corrections and diagnostic logging. Music playback and singing synthesis are
not implemented in this release.

## Stop, preview, quick languages and audio recovery (1.16)

**Stop speaking / cancel pending send** or **Ctrl+Shift+F11** stops current playback
and pending transcript auto-send. Local synthesis and Piper generation cooperate
with cancellation. Google/DeepL/AWS requests already in progress may finish, but
their cancelled output will not play or be sent to the chatbox. The output worker
stays busy until cleanup completes; then a new utterance can start. Already-sent
chatbox text is retained. Animated chatbox sending stops at its next update.

**Preview recognition before sending** is on by default with a 3-second delay.
Change the delay from 0–60 seconds beside the shared editor (0 means immediate).
Recognized text scrolls into view and shows a countdown. Click **Edit message /
pause auto-send** or type to cancel the countdown indefinitely. Click **Speak /
send now** after editing. Recognition waits while a draft or unsent manual text
is present. Clear the editor to release a cancelled draft and receive another.
Editing keeps the recognized message's original Chatbox output setting; manual
pasted messages still use the separate manual Chatbox checkbox. Changes to
preview settings or language pause a pending draft instead of sending it.

**Ctrl+Shift+F12** switches recognition and output together between English and
Polish. Choose another pair under Roleplay settings. Keeping source and target
the same means no DeepL translation. Your selected voices are remembered for each
target language. Windows voices are matched to English/Polish where recognizable;
otherwise choose a matching installed voice. Piper models are also remembered
when selected for a language; no voice models are downloaded automatically.

**Refresh audio devices** and a background scan every 5 seconds rediscover devices
through fresh PortAudio contexts. A missing microphone stops capture and waits
for that same selection to return; a capture error does likewise. Listening
resumes only if it was requested. Use the listening button to cancel recovery.
Changing input while listening restarts capture on the next device scan.
A missing output cancels active output, preserves your selected cable/device,
and never silently falls back to speakers. Reconnect or choose another output,
then send the message again. No automatic replay is performed. Closed-source
hardware/driver failures can still require restarting the audio device or app.

The new keys are editable alongside the existing shortcuts. Enable global
Windows hotkeys to use them while VRChat is focused. Existing settings are kept
when replacing the executable.

## Personality, announcements and expressive delivery

Open **Roleplay → Personality, delivery and hotkeys**. This is separate from
**DeepL translation formality**, which still controls translation only.

Personality presets are Neutral, Helpful assistant, Damaged prototype, Corporate
AI and Rogue intelligence. They supply themed greeting/system/clarification/
goodbye announcements, an optional chatbox tag and a default delivery. They do
not generate AI answers or rewrite ordinary conversations. Your microphone or
pasted words remain yours. Custom announcement fields override preset phrases;
clear a field to use the preset again. Default phrases are English; customize
them if your selected source language is different. All announcement output
uses the existing translation, voice and selected-device pipeline.

Delivery modes apply to all subsequent speech:

| Mode | Effect |
| --- | --- |
| Normal | Normal pacing; existing Polly pitch/whisper settings still apply |
| Measured | Slower pacing |
| Warning | Faster pacing |
| Malfunction | Slower pacing and a short repeated first word |
| Confidential whisper | Genuine Polly whispered effect; requires Polly as primary provider |

Windows SAPI rate changes are approximate; Piper changes phoneme length and
Polly uses SSML rate. Malfunction is a deliberate spoken stutter, not a voice
conversion or electronic distortion filter. It does not duplicate text in the
chatbox. Whisper on a local provider reports a clear message rather than silently
switching to a paid online service. Cycling delivery skips whisper on local
providers. Changing personality selects its default delivery; you can then
choose another delivery yourself. Normal retains any manually selected legacy
Polly effect; set **Extra tags → None** to clear that effect.

Default hotkeys are editable:

| Shortcut | Action |
| --- | --- |
| Ctrl+Alt+F5 | Greeting |
| Ctrl+Alt+F6 | System announcement |
| Ctrl+Alt+F7 | Request clarification |
| Ctrl+Alt+F8 | Goodbye |
| Ctrl+Alt+F9 | Next personality |
| Ctrl+Alt+F10 | Next delivery |
| Ctrl+Alt+F11 | Start/stop listening |
| Ctrl+Alt+F12 | Speak pasted text |
| Ctrl+Shift+F11 | Stop output / cancel auto-send |
| Ctrl+Shift+F12 | Switch quick language pair |

By default shortcuts work while this app is focused. Enable **global Windows
hotkeys** in the dialog to use them while VRChat is focused. Only the configured
combinations are registered; no keyboard hook or keystroke recording is used.
Unavailable/reserved key combinations report a conflict so you can change them.
Bindings support Ctrl/Alt/Shift/Win plus letters, digits or F1–F24 (or an unmodified
function key). Duplicate bindings and multi-stroke sequences are rejected. Clear
a binding to disable it. Global keys are unregistered on reconfiguration and exit.

Announcement actions are also available in the Roleplay menu and through OSC
`/roleplay` with the action names `greeting`, `system`, `uncertain`, `goodbye`,
`cycle_personality`, `cycle_delivery`, `toggle_listener`, or `speak_paste`.
Announcements received during output are dropped with a busy message, not queued.
Personality phrases are roleplay dialogue; they do not change privacy or other
application settings. Personality/delivery changes apply to the next utterance.

The tests simulate Windows registration and SAPI. Global shortcuts in VRChat,
real pacing, and Polly whispered delivery still need a Windows listening test.

## More offline voices: Piper

Install the optional backend into the same Python environment as the app:

```powershell
python -m pip install -e ".[offline]"
```

Download a Piper voice's `.onnx` **and** matching `.onnx.json` files from
[the Piper voice collection](https://huggingface.co/rhasspy/piper-voices/tree/main),
keeping both files together. Select **Speech provider → Piper (offline)**, then
**Choose Piper voice model (.onnx)**. The model's language must match the text
being synthesized. Different model files provide different voices. This first
integration uses the default speaker for multi-speaker models.

Piper synthesizes locally on CPU and uses the selected audio output device.
It makes no model downloads or cloud requests itself. Model selection and
backend installation are required before first use. Optional Polly fallback
works just as for Windows Speech. Piper here uses natural model delivery;
it does not implement Polly's pitch or whispered styles. Genuine whispered
speech needs a voice/model trained for that delivery, rather than simply
lowering playback volume. Polly's existing whispered style remains available.
Kokoro is another potential offline provider, but is not integrated here.

Validation: the Piper command-line interface was exercised and its process,
Unicode input, timeout and audio-output handling have automated tests. Full
synthesis with real Piper voice assets and Windows audio routing remains to
be tested with your downloaded model.

## Keyword additions to OSC chatbox text

1. Open **Edit → Chatbox keyword additions**.
2. Add a keyword and the text/emoji/link to append, for example `hello → 👋`
   or `system → [AI ONLINE]`, then Save.
3. Enable **Show Chatbox settings → Enable keyword text / emoji additions**.

Rules apply to both recognized and pasted messages when their chatbox output
is enabled. They do not affect synthesized speech. Matching ignores case and
uses whole words/phrases, including literal punctuation. Rules inspect the
nickname-corrected source and translated output. Each matching addition is
appended once in table order; additions do not trigger more rules. The original
sentence is retained. Clear a keyword and Save to remove its rule. Rules persist
in `chatbox-rules.json` beside the application settings; the enable toggle also
persists and starts off by default.

Standard VRChat OSC chatbox input is text: it cannot embed a picture or upload
an image. An image URL or Unicode symbol can be added as text, but it will not
render as an inline image. Font support and VRChat's message limits still apply;
keep additions short. Existing animation and font settings still apply.

## Local Windows speech and optional Polly fallback

Open **Show Speech settings → Speech provider → Windows Speech**, then select
an installed voice and your output device (for example Cable Input). This works
for both microphone recognition and pasted text. New configurations default to
Windows Speech; existing configurations keep their saved provider until changed.
No AWS key or network connection is needed for local synthesis. Recognition
still uses Google, and translation still uses DeepL when configured.

The provider uses Windows desktop SAPI voices through `pywin32`, installed
by the project's normal dependency installation on Windows. It renders a temporary
WAV and plays it through the same selected-device mixer as Polly, rather than
sending speech to your default Windows speakers. Temporary WAVs are removed
after playback. Choose a voice that speaks your target language. The voice list
contains SAPI desktop voices; some Narrator/OneCore/natural voices are not
exposed through SAPI and will not appear. Restart the app after installing voices.

**Use Polly if local synthesis fails** is opt-in and can incur AWS usage charges.
Choose its separate fallback voice for the target language and enter your AWS
credentials in Configuration. No Polly client or synthesis request is created
unless local synthesis fails. Audio-device/playback failures do not trigger a
second, potentially duplicated online utterance. An unavailable local engine
can also fall back if this option is enabled. Failures and fallback use appear
in diagnostic logs. With fallback off, failures report an error locally.

Windows voices use their natural pitch and do not support Polly's whispered
style here. Pitch/whisper controls are disabled for Windows Speech; select Polly
to use them. Previously selected effects can still apply to Polly fallback.

## New controls

- Paste a ChatGPT answer or type into **Type or paste text to speak**, then click
  **Speak pasted text**. Listening does not need to be enabled. Enable Speech and
  select a Windows voice, or configure AWS credentials for Polly. The selected
  voice and output device apply; pitch and whispered effects require Polly. When source and target languages differ, the existing
  DeepL translator applies too. Paste at most 2500 characters per message.
- **Also send pasted text to VRChat Chatbox** independently controls manual text
  delivery to OSC. It starts unchecked. Recognition keeps the existing Chatbox
  setting. Chatbox output preserves capitalization.
- **Edit → Nickname corrections** edits a persistent phrase/replacement table.
  Add rows, or clear a phrase to remove it, then Save. Matching ignores case,
  uses whole phrases and prefers longer matches. Replacements happen once,
  before translation and synthesis, for microphone and pasted text alike.
  Use the desired spelling or a phonetic pronunciation. Translation may still
  change a name; use matching source/target languages to avoid translation.
- **File → Open diagnostic logs** opens the logs directory under
  `%APPDATA%/VRChat Speech Assistant`. `application.log` records stages, exception
  types and stack locations, with three rotating backups. `native-crash.log`
  attempts to capture fatal native failures; not every OS/driver crash can be
  captured. Logs omit transcript text, credentials, and provider exception
  messages. Settings and nickname files remain separate from logs. Review logs
  before sharing them because stack paths can identify your Windows user.

Audio output runs in a background worker. Only one message plays at a time;
recognition callbacks received during playback are ignored to reduce feedback.
The app asks you to wait for current output before closing. Qt widget updates
from recognition and OSC are delivered on the GUI thread. These changes address
known thread/mixer hazards but do not establish the cause of every prior crash.

## Development and validation

The live application still requires Windows, audio devices, configured provider
credentials and optionally VRChat/virtual audio cable. An unpublished private
`_config.py` is no longer required; enter your own credentials in Configuration.
Existing private defaults remain compatible. No shared keys are supplied.

Use Python 3.12 and install with `python -m pip install -e ".[tests]"`, then run
`python -m vrchat_speech_assistant.main` from the repository root.
On Linux PyAudio needs PortAudio development headers; installing dependencies
does not make the Windows-only application runnable there.

Run `PYTHONPATH=src python -m pytest -q` on Linux. The headless GUI tests use
actual Qt widgets but simulate Windows sounds, audio devices and cloud services;
they do not prove real recognition, AWS/DeepL access, playback or VRChat delivery.
They use a temporary settings directory. Windows requires equivalent PYTHONPATH
setup (`$env:PYTHONPATH="src"` in PowerShell).

Before release on Windows, verify microphone recognition and pasted text through
your virtual cable, test nickname corrections and translation, toggle manual
chatbox output, disconnect an audio device, and confirm diagnostic logs record
a failure without containing message text or credentials.

---

[![pipeline status](https://gitlab.com/ameliend/vrchat-speech-assistant/badges/main/pipeline.svg)](https://gitlab.com/ameliend/vrchat-speech-assistant/-/commits/main)
[![pylint](https://gitlab.com/ameliend/vrchat-speech-assistant/-/jobs/artifacts/main/raw/public/badges/pylint.svg?job=pylint)](https://gitlab.com/ameliend/vrchat-speech-assistant/-/commits/main)
[![vscode-editor](https://badgen.net/badge/icon/visualstudio?icon=visualstudio&label)](https://code.visualstudio.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![semantic-release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)
[![API Documentation](https://badgen.net/badge/icon/API%20documentation?icon=gitlab&label&color=cyan)](https://ameliend.gitlab.io/vrchat-speech-assistant/build/)

# VRChat Speech Assistant

<p align="center">
  <img src="./src/vrchat_speech_assistant/resources/banner.png">
</p>

The VRChat Speech Assistant allows you to use a **speech to speech, with automatic translation.**
And / or speech to text with the **VRChat chatbox** using OSC protocol.

## ⚠️ Important note about DeepL usage ⚠️

This application comes with a free API key, but if it is used too much, it might not work anymore.

I recommend following [these steps](https://gitlab.com/ameliend/vrchat-speech-assistant/-/blob/main/vrchat_speech_assistant/README.md?ref_type=heads) to provide your own API key by creating an account on DeepL (free).

## ✅ [How to use (Video Tutorial) Click here!](https://youtu.be/NQgI6AiNOs8)

## ⏬ [Download the latest release here!](https://drive.proton.me/urls/8Q7Y4G5NTG#U0oQWAXa8j6y)

#### 📦 [Older releases here](https://drive.proton.me/urls/ENCGB10WWR#XcsiRyzLc4BT)

## 📝 [Changelogs](https://gitlab.com/ameliend/vrchat-speech-assistant/-/blob/main/CHANGELOG.md)

- (Language) Added **Arabic** language support
- (Voice) Added **pitch** feature (between -50% and +50%)
- (Chatbox) Added the functionality to clear the Chatbox
- (Chatbox) Added the VRChat SFX sound of the chatbox on the last generation ([92e8594](https://gitlab.com/ameliend/chatbox_osc/-/commit/92e859435494c50107f02dd67fa5fe129e9e2b59))
- (OSC) Ability to change the OSC port from the server

## 🌐 **It works 100% ONLINE.**

- You don't need to download an offline model.
- It won't use your CPU or GPU.

## 🚀 **It is FAST and ACURATE.**

- The application uses Google Cloud Speech-to-Text API, it is constantly updated.

## 🔣 **TRANSLATE over 30+ languages.**

- The translation is provided by DeepL, the best translator to date.

## ✨ **CUSTOMIZE Chatbox with fonts and writing animation.**

- You can activate a writing animation with the Chatbox and over 15 fonts.

## 🔧 Configuration

<p align="center">
  <img src="./vrchat_speech_assistant/resources/screenshot.png">
</p>

1. Select your **Input device**, speak clearly, as you were in a podcast, and avoid any
   source of background noise.
1. Select a **Source language**, it is the language in which you speak for voice recognition.
2. Select a **Target language**, it is the language in which you want to speak,
   if the target language is different from the source language then the translation will be automatic.
3. Select **Speech** if you want to output the result of the recognizer to the desired audio output.
   For the speech to be transmitted to a microphone source, you need to install a
   **Virtual Cable** first, then select the audio output to **Cable Input**.
4. Select the **Voice** if available, it is linked to the target language.
5. Select **VRChat Chatbox** if you want to output into a text your recognition to the VRChat Chatbox.
   (Requires activation of the OSC feature in VRChat)

## 🔌 Virtual Cable setup

To be able to read your speech in VRChat, you will have to install a virtual cable first.

https://vb-audio.com/Cable/

Then select it from the input device.

<p align="center">
  <img src="./vrchat_speech_assistant/resources/device.png">
</p>

## 💬 VRChat Chatbox setup (OSC)

Make sure your OSC feature is enabled in VRChat.

<p align="center">
  <img src="./vrchat_speech_assistant/resources/activate.jpg">
</p>

And that's it, no need for additional configuration.

## 🌟 Super-duper cool alternatives

If you are looking for alternatives, here are some similar applications
that provide other great features!

[Whispering Tiger (Live Translate/Transcribe)](https://github.com/Sharrnah/whispering)

[TTS-Voice-Wizard](https://github.com/VRCWizard/TTS-Voice-Wizard)

[TaSTT: A deliciously free STT](https://github.com/yum-food/TaSTT)

[VRCTextboxSTT](https://github.com/I5UCC/VRCTextboxSTT)

## 🧨 Feature request of find a bug?

You can contact me by mail `a.deshams+git@slmail.me`, or better, create a ticket in this repository!

## Building and publishing the Windows executable

GitHub Actions builds on Windows Server 2022 with Python 3.12. Manual workflow runs
produce a downloadable build artifact; pushing a `v*` tag publishes
a GitHub prerelease **only after tests and executable smoke checks pass**.
The smoke test opens the packaged GUI and synthesizes a real SAPI WAV without
requiring a microphone, network credentials or a physical playback device.
It does not validate microphone recognition or VRChat output on user hardware.

To build locally on Windows:

```powershell
python -m pip install -c requirements-release.txt -e ".[tests]" PyInstaller numpy
python -m pytest -q
python scripts/build_windows.py
```

The executable is `dist/VRChatSpeechAssistantDeluxe.exe`. The build intentionally
excludes private `_config.py` files and Piper's optional runtime/models. It is
unsigned because no signing certificate is configured. Download SHA256 checksums,
third-party notices and smoke-test results alongside the executable in Releases.
The existing MIT attribution is preserved. Dependency source/project links and
licenses are listed in the notices; the build scripts and dependency constraints
are available here to rebuild the executable.
