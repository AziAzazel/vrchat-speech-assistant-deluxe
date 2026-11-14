VRChat Speech Assistant Deluxe 1.28.0 release candidate 1

SRT lyrics now use the selected VRChat Chatbox font/style, including Magic and
UpsideDown. The selected style is captured when a recording starts and applied
to each full caption before enforcing the Unicode-aware VRChat text limit.

Ignore stage directions inside balanced square brackets, including nested or
multiline descriptions, and remove # characters. Empty cleaned captions are
skipped; remaining lyric timestamps and subtitle offset are unchanged.

Show 🎵 from playback start until the first visible lyric, including introductory
SRT entries containing only [Music] or other ignored descriptions. Later gaps
stay blank. Stop and playback completion clear the note/caption. Existing caption
rate limiting remains in effect, including very short introductions.

Windows and Linux share these changes. Download the Windows .exe or Linux x86-64
.tar.gz and replace the old application files; settings remain in the user folder.
Select your desired Chatbox font before starting the recording.

Validation covers Magic/UpsideDown, overlapping cues, styled/emoji UTF-16 limits,
markup/entity cleaning, intro/offset/rewind, playback routes and cancellation.
Packaged Windows checks play WAV/MP3 with cleaned Magic captions; Linux keeps its
real virtual-microphone, GUI and OSC checks. VRChat reception requires user testing.
