# Upstream review and integration boundary

Reviewed 2026-11-10. Original project: **VRChat Speech Assistant**, Amelien Deshams
(Nekosan), MIT license, <https://gitlab.com/ameliend/vrchat-speech-assistant>.

- Deluxe began from the GitHub mirror `dmportella/vrchat-speech-assistant`, commit
  `ab436365b487dc77c2fba912b99b66dd746ee6f8`, labelled 1.14.0.
- Its five main code files (`main`, `providers`, `languages`, `widgets`, `utils`)
  are byte-identical to upstream commit `87e53833c36d8a2c50040b44b8e7fa4b50257cfe`
  from September 2024. The mirror was therefore a dated snapshot.
- Upstream main was at `2346a3f1984c7fdfe301b36616a2686a1357d378`, version 2.3.1,
  dated August 2026. Deluxe's version numbers do not represent upstream releases.
- The mirror intentionally omits old Git history; its MIRROR.md cites AWS keys
  in that history. No upstream history or shared credentials were merged here.
  Selected source changes were adapted; existing MIT attribution is preserved.

## Adapted in Deluxe 1.18

| Upstream commit | Change | Adaptation |
| --- | --- | --- |
| [9e247e2](https://gitlab.com/ameliend/vrchat-speech-assistant/-/commit/9e247e25a6f96f29b052c22d4d2cb8c04ce0c8cc) | Expanded languages and Polly engine mapping | 86 recognition language entries, 111 DeepL entries, 100 distinct Polly voice IDs. Existing labels, order, saved choices and Standard engines are retained; additional Neural voices are labelled. Beta flags and quality model are used only when a selected language is outside the legacy set. |
| [5592443](https://gitlab.com/ameliend/vrchat-speech-assistant/-/commit/55924433f87fa3e40fcc5362066c58e967de27a9) | Timing diagnostics | Log stage durations for recognition, translation, synthesis/playback and OSC. No transcripts, keys or raw provider exception messages are added to logs. |

Neural voices cannot use the same pitch/whisper/auto-breaths SSML as Standard
voices. Deluxe preflights unsupported combinations with an actionable message,
keeps saved pitch, and uses Neural-compatible escaped SSML. Existing Standard
voice audio caches remain valid. Normal English/Polish translation requests keep
their prior options. New language/voice availability still depends on the actual
provider/account/region or installed local voice/model. No live AWS/DeepL requests
were made during integration tests; API request construction is tested with mocks.

## Equivalent fixes already present

- `2289526` fixes the obsolete `pyaudio_devices.devices` import. Deluxe first
  corrected it and now owns fresh PortAudio enumeration for reconnect handling.
- `96cac22` removes default AWS/DeepL credentials. Deluxe's defaults are empty;
  private `_config.py` is excluded from executables. The optional legacy module
  remains compatible in source installations only.

## Not imported wholesale

- `12851a8` and `b48c679`: replace playback with `audio_reader_osc`, then fix its
  required Path argument. Deluxe has its own serialized, cancellable playback.
  Moreover, the dependency repository's current HEAD identifies as `audio_reader`
  and advertises migration to Verba, while upstream still imports
  `audio_reader_osc`. Blindly following that unpinned dependency needs investigation.
- `a56f688`: rename INI keys. No benefit sufficient to risk existing Deluxe profiles.
- `293fc1d`: CLI interface; `321f94a`: configurable OSC destination IP. Potential
  later features; not required for the current local VRChat GUI workflow.
- Build/template/style/generated-documentation changes: not runtime fixes for
  Deluxe's tested Windows executable pipeline. Qt/dependency updates need their
  own packaging/regression validation rather than a blanket version bump.

## Separate experimental branches (not upstream main)

- [whisper / 3b62611](https://gitlab.com/ameliend/vrchat-speech-assistant/-/commit/3b62611):
  local OpenAI Whisper recognition; `651beab` chooses the small model. A useful
  future optional backend, requiring model assets and PyTorch/runtime packaging.
  Whisper recognition is distinct from the whispered voice effect.
- [ggwave / 5c72a8d](https://gitlab.com/ameliend/vrchat-speech-assistant/-/commit/5c72a8d):
  encode text as modem-like audio ("Sad"/"Cheerful" protocol presets). Interesting
  AI roleplay sounds, not ordinary intelligible speech or singing. Adds native
  dependencies and needs a separate Windows distribution check.
- `Cloud-Speech-to-Text-API / e52de84`: Google Cloud backend requiring additional
  credentials/dependencies; increases cloud dependence, unlike local Whisper.

To review future upstream changes, compare the pinned references above and port
selected fixes into Deluxe with tests. Do not merge rewritten upstream history,
replace the entire app, or import credentials/experimental branches automatically.
