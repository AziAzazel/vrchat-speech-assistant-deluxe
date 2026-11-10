VRChat Speech Assistant Deluxe 1.18.0 release candidate 1

Download VRChatSpeechAssistantDeluxe.exe (Windows x64). Existing settings remain
in %APPDATA%/VRChat Speech Assistant.

Selected changes adapted from the original Amelien Deshams (Nekosan) project:
- Expanded catalogues: 86 recognition languages, 111 DeepL languages and 100
  distinct Polly voice IDs. Additional DeepL languages request the beta flag
  and quality-optimized model; actual availability depends on DeepL.
- Correct engine selection for newly added Neural voices, including Polish Ola.
  Neural uses supported SSML; incompatible whisper/pitch settings produce an
  actionable message before synthesis. Standard voices retain their effects,
  labels, saved selections and cache behavior.
- Duration diagnostics for recognition, translation, synthesis/playback and OSC,
  without adding transcripts or credentials to logs.
- UPSTREAM_REVIEW.md documents the exact baseline, selected commits and deferred
  experiments. No old upstream history or shared credentials were merged.

All previous Deluxe controls remain available. Offline Whisper recognition and
GGWave are separate upstream experiments and are not included in this release.

Validation includes regression tests and a packaged Windows smoke test covering
native hotkeys, SAPI generation, GUI, saved settings and the Neural style guard.
Live AWS/DeepL calls and audio/VRChat routing require user testing. The executable
is unsigned.
