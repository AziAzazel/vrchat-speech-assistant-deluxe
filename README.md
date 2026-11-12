# VRChat Speech Assistant Deluxe

<p align="center">
  <img src="./Logo%20VR%20Chat%20Speech%20Assistant%20Deluxe.png" alt="VRChat Speech Assistant Deluxe — official project logo" width="420">
</p>

VRChat Speech Assistant Deluxe is based on [VRChat Speech Assistant](https://gitlab.com/ameliend/vrchat-speech-assistant), originally developed by **Amelien Deshams (Nekosan)**.

[Download the Windows executable](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases)

This is vibe-coded but works better than the original in my opinion. If there are any bugs let me know!

The standalone Windows x64 download includes Windows speech, Polly, translation,
manual text speech and the roleplay controls. No Python installation is needed
for those features. Piper remains an optional external backend: install Piper
separately and select its `piper.exe` and voice assets in Speech settings.


This fork preserves the original Google recognition, DeepL translation, Amazon
Polly synthesis and VRChat OSC workflow. It adds manual text input, nickname
corrections and diagnostic logging. Music playback and singing synthesis are
not implemented in this release.

## Immediate speech captions and readable long messages (1.23)

Chatbox output now starts **before synthesis/playback**, instead of waiting until
the whole utterance finishes. Long text is formatted once, split into pages that
fit VRChat's 144 UTF-16-unit limit (including emoji/styled letters), and advanced
while audio plays. Each page appears in full immediately; the old per-character
typing animation is disabled for live captions and its legacy setting is migrated
off. This prevents the old animation delay and rapid replacement by the last page.

Windows Speech, Piper and Polly keep a **single complete synthesis/playback** per
utterance. Page timing follows audio position and duration, with boundaries
estimated proportionally from page lengths; this is not word-level alignment.
WAV duration is read from its header; other supported speech audio uses decoded
length. Duration lookup is only needed for multi-page captions. If duration is
unavailable a reading-time estimate is used. No extra Polly speech-mark or
per-page synthesis requests are added. All pages are retained: very short audio
or slow frames can leave a readable remainder after playback rather than drop it.
Text-only messages advance with reading time. Updates respect a minimum 1.5 s
interval; Stop cancels every future page and leaves already visible text in place.

Recognition/translation and the existing editable-preview countdown still happen
before an utterance is accepted. To remove the review delay, disable transcript
preview or reduce its delay in the message section. Google recognition still
returns completed audio fragments, not interim word-by-word text. The fix removes
the extra wait for TTS completion, not the recognition service's processing time.
SRT recordings and YouTube playback keep their separate behavior.

## Maintenance and performance (1.22)

- Indexed SRT timing avoids scanning every subtitle at each playback tick.
- Settings skip unchanged writes, batch startup/language-switch updates and use
  atomic replacement. Pitch/ending sliders update live but persist once released.
- Cloud SDKs and pygame load when needed; Polly clients and successful validation
  are reused until keys/region change. Credential-check audio streams are closed.
- Device probes enumerate once with one PortAudio context, still in an isolated
  process. OSC handlers belong to each window; closed YouTube panels stop polling.
- Unused direct dependencies, obsolete controls, generated documentation and the
  inactive GitLab release setup were removed. Source docs and attribution remain.
- Windows bundles retain Polly models, shared AWS metadata and TLS certificates;
  unused AWS service models are excluded. Polly/fallback functionality remains.

[Review, reproducible measurements and validation limits](MAINTENANCE_REVIEW.md)
explain what was measured. These are component improvements, not a claim that
all speech, network requests or application startup run at the same speedup.

## YouTube player without captions (1.21)

Open **Roleplay → YouTube player (no captions)**, paste a YouTube video link and
click **Open / replace video**. Deluxe opens a dedicated Microsoft Edge app
window with the normal YouTube page and controls. Start playback there; pause,
seek and volume are YouTube controls. Watch/share/Shorts/live video links are
accepted. Microsoft Edge must already be installed on Windows. No downloader,
media extraction, ad bypass, YouTube API key or subtitle scraping is used.
Streaming uses normal browser buffering/cache; it does not export audio files.
YouTube consent, ads, account requirements and video availability still apply.

**Route the browser separately:** start playback, use **Windows volume mixer**,
then set **Microsoft Edge** output to your VB-CABLE input (or other VRChat audio
route). Edge does **not** follow Deluxe's Speech output selector. Windows may
apply the same Edge audio preference to ordinary Edge windows as well.
There are no OSC captions or automatic speech/translations from the video.

**Stop YouTube**, the global **Stop speaking** action, closing the player panel,
or closing Deluxe terminates the owned player. Ordinary Edge windows are not
closed. This uses a dedicated browser profile in the app's data folder and a
Windows job that also owns the player's renderer/audio processes. The browser
profile has its own normal cookies/cache; media is not copied into Soundboard.
YouTube playback is independent of the local speech/recording busy state and can
play alongside them; Stop speaking stops both. Use the YouTube controls to pause
without stopping other output. Linux/source installations show a Windows/Edge
requirement instead of launching another browser.

## WAV / MP3 recordings, SRT subtitles and shortcut recording (1.20)

Open **Roleplay → Soundboard phrases and hotkeys → Add recording**. Choose a
WAV/MP3 file and, optionally, its SRT. A same-name `.srt` beside a recording is
suggested automatically. Set a shortcut, output route and subtitle offset:
**+300 ms delays** subtitles; negative values advance them. Save the recording,
then save the Soundboard list. **Files / SRT…** edits an existing recording.
Files remain on your computer; configuration stores paths, not copies. Moving a
file requires selecting it again. No AWS, DeepL or synthesis is used for playback.

For recordings, **Voice only** plays audio, **Voice + chatbox** adds timed captions,
and **Chatbox only** runs the subtitle timeline silently without an audio device.
Audio uses the application's chosen output device. Captions use audio playback
position, not the text animation setting. SRT supports UTF-8/BOM, UTF-16/BOM and
Windows Central European encoding, multiline cues and common formatting tags.
Overlapping cues share a message. Lines are limited to 144 characters and updates
to one per 1.5 seconds: rapid obsolete cues are skipped instead of queued. This is
line synchronization, not word highlighting. Captions beyond the recording's end
are cut off; chatbox timing also depends on VRChat and audio-routing latency.

**Stop speaking** cancels playback and future captions, and attempts to clear the
last caption. Soundboard settings also have a **Stop** button for previews.
Normal speech and recordings share the existing single-output busy/cancel flow.

Shortcut fields now record one chord immediately, including `Ctrl+;`.
Click a field and press the keys; Backspace/Delete clears it. The application's
Windows registrations and Qt shortcuts are suspended while shortcut settings are
open, including nested recording settings, and restored after Save, Cancel or
closing the dialog. This prevents existing bindings from swallowing recorded keys
or accidentally playing a phrase. Other applications can still reserve a key;
registration conflicts remain visible after settings close.

## Soundboard phrases and hotkeys (1.19)

Open **Roleplay → Soundboard phrases and hotkeys**. Each row has its own shortcut,
phrase, language, output route, provider and voice. Add up to 32 rows, remove rows,
or clear a shortcut to disable it. **Play selected** previews the row before saving.
Duplicate bindings across Soundboard and Roleplay are rejected. Global shortcuts
work while VRChat is focused when **Global hotkeys** is enabled; registration
conflicts are reported in the app. Punctuation keys follow the Windows keyboard
layout, including **Ctrl+;**.

The initial example is **Ctrl+; → ぽい (poi), Japanese, Voice only, Polly Mizuki**.
Polly requires your configured AWS keys. For offline speech select an installed
Japanese Windows desktop voice or a configured Japanese Piper model. The language
field does not install a voice or translate text: enter the phrase in that language.
Piper uses the model saved for that language, or the current configured model.

- **Voice only**: speech through the selected application output device; no chatbox
  text or typing status from the phrase.
- **Chatbox only**: OSC text without synthesis, AWS keys or an audio device.
- **Voice + chatbox**: speech followed by chatbox output.

Routes explicitly override the main Speech/Chatbox toggles for the saved phrase.
The main language, voice, microphone state and unsent editor text stay intact.
An active preview countdown is paused. Phrases use normal delivery, bypass DeepL,
nickname/pronunciation substitutions, random endings and chatbox decorations, so
saved text is sent consistently. Spoken output requires the selected audio device;
there is no automatic cloud fallback. Busy output refuses another phrase rather
than queueing it. **Stop speaking** also cancels soundboard playback and unsent OSC.
Settings are saved in config.ini, and attempts appear in the existing session history.

## Audio crash fix (1.18.0rc2)

Device refresh now runs in a disposable helper process. It cannot initialize or
terminate PortAudio alongside microphone capture in the application, which could
cause a native Windows access violation when enabling listening during a scan.
A failed or timed-out scan preserves the last device list and capture state;
subsequent scans retry. Successful scans still detect disconnected/reconnected
devices. Diagnostics record helper exit codes without device names or speech.

## Selected upstream updates (1.18)

We reviewed the original GitLab project through release 2.3.1 and adapted selected
changes into Deluxe. [Upstream review and commit references](UPSTREAM_REVIEW.md)
explain the shared baseline, incorporated fixes and experimental branches.

- Recognition catalogue: 86 languages; DeepL catalogue: 111 languages. Additional
  DeepL languages use its beta flag and quality-optimized model. Actual API
  availability depends on the service; these counts describe our catalogue.
- Polly catalogue: 100 distinct voice IDs, including Polish **Ola [Neural]**.
  New voices select the required engine. Existing voice labels, saved selections
  and Standard effects remain compatible.
- Neural voices support rate, but cannot use whisper or pitch. The UI explains
  this and rejects incompatible settings before a synthesis request; choose a
  Standard voice for those effects. The same guard applies to Polly fallback.
- Diagnostic logs include durations for recognition, translation, synthesis with
  playback, and OSC delivery, without recording submitted text or credentials.

Offline recognition from the upstream experimental Whisper branch is not yet
included. Recognition still uses Google; Windows Speech and Piper remain the
local synthesis options. No live AWS/DeepL requests were made for this update.

## Pronunciation, history, collapsible sections and random endings (1.17)

**Edit → Pronunciation dictionary (speech only)** maps a displayed name/word to a
spoken respelling, for example `Nekosan → Neko-san`. Matching ignores case and uses
whole words/phrases. Rules run after translation and the optional ending, just
before synthesis. They never change chatbox spelling. These are literal text
respellings, not IPA/SSML commands. The older nickname corrections still apply
before translation to both outputs; pronunciation is a separate dictionary,
saved in `pronunciation.json` alongside configuration.

**Session history** is available from File or the message section. It keeps the
last 50 accepted output attempts in memory only, with original text, resulting
text, spoken pronunciation, language/voice and completed/cancelled/failed status.
It is not written to disk or diagnostic logs and starts empty after restart.
Clear history removes its current entries. A failed or cancelled entry does not
mean every output was delivered: speech may have played before a chatbox failure.

- **Load original into editor** lets you correct and send again using current
  translation/settings. It refuses to replace an unsent draft; clear or send that
  draft first.
- **Repeat result** speaks the selected result with current voice, pronunciation
  and delivery settings. It skips translation, nickname correction and another
  ending lottery, so the existing ending is not duplicated. Current chatbox
  effects and the manual Chatbox toggle still apply.

Click any section header to collapse/expand its entire category. Voice settings,
Chatbox and Random ending start collapsed. Every section's state is remembered.
Recognition preview automatically opens the message section when needed so an
editable draft/countdown is not hidden. The former inner Show settings controls
are replaced by these whole-section headers.

Open **Random ending**, enter a suffix such as `, poi` or `, desu`, and set the
frequency slider: **0% never**, **100% always**, other values are a probability for
each accepted utterance, not a fixed every-N counter. It starts at 0% with no
text, so nothing changes until configured. Both the text (up to 120 characters)
and frequency are remembered. One lottery is made after translation for the
whole utterance, shared by speech/chatbox and any Polly fallback. A leading comma
attaches directly; a bare word gets a separating space. Final punctuation is
kept after the ending (`Hello! → Hello, poi!`). Pronunciation changes only the
spoken copy. Chatbox keyword additions may also match the resulting ending.

## Focus-independent hotkeys, saved voices and responsive UI (1.16.1)

Global Windows hotkeys are enabled by default, including a one-time migration
of older focus-only configurations. A visible **Global hotkeys (also outside
this app)** checkbox controls this setting; if you turn it off, your opt-out
is saved. The registration count is displayed below it. Conflicts are reported
and recorded in diagnostic logs; customize a conflicting key in Roleplay settings.
The message queue is initialized before registration. Windows reserves F12 for
debugging, so old default F12 bindings are migrated once: language switching is
now **Ctrl+Shift+F10**, pasted speech **Ctrl+Shift+F8**, Stop **Ctrl+Shift+F11**.
Other custom bindings are retained. The Windows build tests actual native
registration and background WM_HOTKEY dispatch without a focused Qt window.
Specific games, overlays and keyboard utilities still need a user hardware test.

Voice selection is remembered for each **provider + target language**, whether
you use a language dropdown or the quick-switch hotkey. Polly fallback voice
choices are remembered by target language too. Voice pitch is saved immediately
and restored at launch, including the actual Polly synthesis setting. Local
providers still do not support Polly's pitch effect.

The interface reflows whole sections into 1, 2 or 3 columns as you widen the
window. Descriptions wrap, controls expand with their section, and the banner is
compact. Narrow windows retain vertical scrolling. The last normal window size
and maximized state are restored, with dimensions clamped to the current screen.

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

**Ctrl+Shift+F10** switches recognition and output together between English and
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
| Ctrl+Shift+F8 | Speak pasted text |
| Ctrl+Shift+F11 | Stop output / cancel auto-send |
| Ctrl+Shift+F10 | Switch quick language pair |

Global Windows hotkeys are enabled by default. Turn **global Windows hotkeys**
off to restrict shortcuts to this app while focused. Only the configured
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
3. Enable **VRChat Chatbox → Enable keyword text / emoji additions**.

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

Open **Voice settings → Speech provider → Windows Speech**, then select
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
