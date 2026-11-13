# User guide

[Project overview](../README.md) · [Changelog / historia zmian](../CHANGELOG.md) · [Developer guide](DEVELOPMENT.md)

This guide describes the current Deluxe application. For changes between releases,
see the changelog. Windows x64 is the supported standalone platform.

## First setup: VRChat, virtual cable and OSC

1. Download `VRChatSpeechAssistantDeluxe.exe` from [Releases](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases).
2. Install [VB-CABLE](https://vb-audio.com/Cable/) or use your existing virtual audio setup.
3. In Deluxe, choose your real microphone as **Input device** and **CABLE Input**
   as the speech output. In VRChat, choose **CABLE Output** as the microphone.
4. Choose a source/target language and a voice that speaks the target language.
   Matching source/target languages avoid translation.
5. Enable OSC in VRChat to show text in its chatbox; enable **VRChat Chatbox** in Deluxe.
6. Configure your own DeepL/AWS keys only for the services you use. No shared keys
   are included. Windows desktop speech needs no AWS key; recognition still uses Google online.

The standalone download needs no Python for Windows Speech, Polly or translation.
Piper is an optional external backend. YouTube uses installed Microsoft Edge and
has separate audio routing, described below. Singing synthesis is not implemented;
local recordings/music playback are available through Soundboard.

## Local Windows speech and Polly fallback

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

## Offline voices with Piper

For the standalone executable, install Piper separately, then choose its executable
and voice/model in Speech settings. For a source installation, the optional backend
can be installed into the same Python environment as the app:

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

## Manual text, nickname corrections and diagnostic logs

- Paste a ChatGPT answer or type into the main editor, then click
  **Speak / send now**. Listening does not need to be enabled. Enable Speech and
  select a Windows voice, or configure AWS credentials for Polly. The selected
  voice and output device apply; pitch and whispered effects require Polly. When source and target languages differ, the existing
  DeepL translator applies too. Paste at most 2500 characters per message.
- **Send manual text to Chatbox** independently controls manual text
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

## Chatbox page preview and separate display text

The **Message preview and speech** card shows how the editor text will be divided
into pages above your avatar. Use **← / →** to browse them; the counter shows the
current page, total pages and use of VRChat's text limit. Emoji and styled fonts
are counted using the same rules as actual output. Previewing does not send OSC
or synthesize audio.

The draft preview includes nickname corrections, selected font and configured
chatbox additions/personality tag. Translation and random endings may change the
final text: after processing, the preview updates to the final pages for that
output. A late result does not overwrite a newer editor draft. It is a text/layout
preview, not an exact rendering of the font available inside VRChat.

To display something different from the spoken message, enable **Use separate
Chatbox text (manual / edited draft)** and enter the desired text/emoji/action in
the second editor. For example, speak “I can answer your question” while displaying
`*patrzy podejrzliwie* 👀`. Enable **Send manual text to Chatbox** as well (edited
recognition drafts use the main recognition Chatbox setting).

Separate text is not spoken, translated, or extended by keyword/personality
additions; the selected font still applies. Blank uses the usual spoken-message
text. Each editor accepts up to 2500 characters for sending. Editing either pauses
pending auto-send. The fields remain session-only; session history keeps separate
text for Repeat, which still uses your current voice settings. A fresh recognized
preview clears the previous separate action to avoid reusing it accidentally.

## Favorite reactions on large buttons

The **Favorite reactions** card provides large buttons for saved Soundboard
entries. On first upgrade, if the selected output language is Polish or English,
up to six starters are added once using the current provider/voice: **Tak / Nie /
Chodź / Poczekaj / Nie rozumiem / Powtórz**, or their English equivalents. Existing
rows remain intact; the combined Soundboard limit stays at 32. Other languages or
a full Soundboard can use favorites selected manually.

Open **Edit favorites / Soundboard…** and mark **Favorite ★** on any phrase or
recording, then Save. Edit its text to change the button label; longer labels are
shortened on the button with full text in the tooltip. A keyboard shortcut is
optional. Uncheck Favorite to hide a button without deleting the entry.

One click plays the saved row directly, preserving its language, voice, pitch,
delivery, output route and separate chatbox text (or the recording's SRT). Starter
rows use **Voice + chatbox**. Choose a matching installed/configured voice for each
row; changing the main language later does not change saved reactions. Buttons
are disabled during output; Stop remains available. Unsent editor text is retained.
This category reflows with the window and can be collapsed like other settings.

## Live speech captions and long messages

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

## Transcript preview, cancellation, language switching and device recovery

**Stop speaking / cancel pending send** or **Ctrl+Shift+F11** stops current playback
and pending transcript auto-send. Local synthesis and Piper generation cooperate
with cancellation. Google/DeepL/AWS requests already in progress may finish, but
their cancelled output will not play or be sent to the chatbox. The output worker
stays busy until cleanup completes; then a new utterance can start. Already-sent
chatbox text is retained. Future chatbox pages are cancelled; already visible text remains.

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

## Global hotkeys, saved voices and window layout

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
choices are remembered by target language too. Voice pitch updates live and is saved when a dragged slider is released
(or immediately for keyboard/programmatic changes), then restored at launch, including the actual Polly synthesis setting. Local
providers still do not support Polly's pitch effect.

The interface reflows whole sections into 1, 2 or 3 columns as you widen the
window. Descriptions wrap, controls expand with their section, and the banner is
compact. Narrow windows retain vertical scrolling. The last normal window size
and maximized state are restored, with dimensions clamped to the current screen.

## Personality, announcements and delivery

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
| Confidential whisper | Polly whispered effect; requires a Standard voice with Polly as primary provider |

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
Bindings support Ctrl/Alt/Shift/Win plus letters, digits, supported punctuation (including `;`) or F1–F24 (or an unmodified
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

## Pronunciation, history, collapsible sections and random endings

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
mean every output was delivered: one output may already have arrived when the other fails, including captions shown before a synthesis failure.

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

## Keyword text and emoji additions

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
keep additions short. Font settings still apply; live captions bypass the obsolete typing animation.

## Soundboard phrases and hotkeys

Open **Roleplay → Soundboard phrases and hotkeys**. Each row has its own shortcut,
phrase, language, output route, provider and voice. Add up to 32 rows, remove rows,
or clear a shortcut to disable it. **Play selected** previews the row before saving.
Duplicate bindings across Soundboard and Roleplay are rejected. Global shortcuts
work while VRChat is focused when **Global hotkeys** is enabled; registration
conflicts are reported in the app. Punctuation keys follow the Windows keyboard
layout, including **Ctrl+;**.

The initial example is **Ctrl+; → ぽい (poi), Japanese, Voice only, Polly Mizuki**.
For independent speech and text, enter the spoken phrase in **Speech / name** and
the text/emoji to display in **Chatbox text**. Leave Chatbox text blank to retain
the old behavior (show the spoken phrase). The output route controls whether
speech, chatbox text or both are sent; recordings continue to use SRT captions.

Example: **Ctrl+;**, speech **ぽい**, chatbox **👀**, language **Japanese**,
output **Voice + chatbox**, provider **Amazon Polly**, voice **Mizuki**,
delivery **Whispered**. The eyes appear before synthesis, while only ぽい is
spoken. **Delivery** belongs to the row and does not change the main speech style.
Whisper requires a Polly Standard voice; Windows/Piper and Polly Neural voices
cannot provide this effect. Unsupported spoken combinations are rejected before
output. Existing rows default to Normal delivery and matching speech/chatbox text.

**Pitch** sets the saved phrase's pitch from **−50% to +50%**, independently of
the main Voice pitch slider. **0%** keeps the natural pitch and is the default for
older rows. Pitch can be combined with Whispered delivery. A nonzero value needs
a **Polly Standard** voice, such as Mizuki; use 0% for Windows/Piper or Polly Neural.
Chatbox-only entries retain the setting without applying it. Pitch and delivery
are disabled for recordings, which keep their original audio.

Polly requires your configured AWS keys. For offline speech select an installed
Japanese Windows desktop voice or a configured Japanese Piper model. The language
field does not install a voice or translate text: enter the phrase in that language.
Piper uses the model saved for that language, or the current configured model.

- **Voice only**: speech through the selected application output device; no chatbox
  text or typing status from the phrase.
- **Chatbox only**: OSC text without synthesis, AWS keys or an audio device.
- **Voice + chatbox**: the first chatbox page appears before speech; further pages advance during playback.

Routes explicitly override the main Speech/Chatbox toggles for the saved phrase.
The main language, voice, microphone state and unsent editor text stay intact.
An active preview countdown is paused. Phrases use their saved delivery and bypass DeepL,
nickname/pronunciation substitutions, random endings and chatbox decorations, so
saved text is sent consistently. Spoken output requires the selected audio device;
there is no automatic cloud fallback. Busy output refuses another phrase rather
than queueing it. **Stop speaking** also cancels soundboard playback and unsent OSC.
Settings are saved in config.ini, and attempts appear in the existing session history.

## WAV / MP3 recordings and SRT subtitles

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

## YouTube player without chatbox captions

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

## Language catalogue and voice capabilities

We reviewed the original GitLab project through release 2.3.1 and adapted selected
changes into Deluxe. [Upstream review and commit references](../UPSTREAM_REVIEW.md)
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
local synthesis options. Availability depends on the provider/account and installed local voice/model.

## Settings and private files

Configuration is created automatically in `%APPDATA%/VRChat Speech Assistant`.
Replacing the executable preserves settings. `config.ini` can contain your API
keys in plain text: keep it private. Dictionary/rule files are stored beside it;
logs are in the `logs` subdirectory. Session history stays in memory only.

[Back to README](../README.md) · [Release history](../CHANGELOG.md)
