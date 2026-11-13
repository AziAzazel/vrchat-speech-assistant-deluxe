# Changelog / Historia zmian

[README](README.md) · [User guide](docs/USAGE.md) · [Download releases](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases)

## VRChat Speech Assistant Deluxe

Newest first. Entries identify the published release candidate used for each
feature set; build-only candidate attempts are not separate feature releases.
For full operating instructions, use the user guide rather than this history.

### [1.25.0rc1](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.25.0rc1) — Soundboard phrase pitch

- Add a saved −50% to +50% Pitch control per Soundboard phrase, independent of the main pitch slider. Existing phrases default to 0%.
- Combine pitch with Whispered delivery on Polly Standard voices such as Mizuki. Reject unsupported nonzero pitch on local/Neural voices before output.
- Preserve text-only routing and recording playback. Expand the settings window and cover pitch boundaries, validation and persistence in automated tests and packaged Windows checks.

### [1.24.0rc1](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.24.0rc1) — Separate Soundboard speech and chatbox text

- Save independent chatbox text/emoji for each Soundboard phrase. Blank uses the spoken phrase, preserving existing shortcuts.
- Add per-phrase Normal/Whispered delivery, independent of the main speech settings. Whisper requires a Polly Standard voice; unsupported spoken combinations are rejected before output.
- Support one shortcut displaying 👀 while speaking Japanese ぽい with Polly Mizuki in Whispered delivery. Voice-only and chatbox-only routes remain available; recordings still use SRT captions.
- Preserve the main voice/language and editor draft. Add persistence, output-route and style validation tests, plus packaged Windows checks for the new controls.

### [1.23.0rc1](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.23.0rc1) — Live chatbox captions

- Show the first text page before synthesis/playback rather than after the whole voice clip finishes.
- Advance long messages during playback using the audio clock and approximate page timing, preserving all pages. Split text within the VRChat UTF-16 limit, including emoji and styled letters.
- Disable the delayed typewriter animation. Keep one complete synthesis per utterance, with no extra per-page Polly requests.
- Pace text-only pages for reading and cancel future pages with Stop. Recognition/translation and the editable-preview countdown still occur before output.

### [1.22.0rc1](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.22.0rc1) — Cleanup and performance

- Index SRT cue boundaries instead of rescanning every subtitle on each playback tick.
- Deduplicate and batch settings writes, replace configuration atomically, and persist dragged sliders on release.
- Load cloud SDKs/pygame when needed, reuse Polly clients and successful validation, and close validation streams.
- Use one PortAudio enumeration per isolated scan, per-window OSC handlers, and stop polling closed YouTube panels.
- Remove unused dependencies, generated documentation and inactive GitLab release setup. Exclude unused AWS service models while retaining Polly and shared SDK data.
- Windows executable reduced from 124.5 MB to 109.1 MB. See [measurements and limits](MAINTENANCE_REVIEW.md).

### [1.21.0rc4](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.21.0rc4) — YouTube audio player

- Add Roleplay → YouTube player (no captions), opening normal YouTube playback in a dedicated Microsoft Edge app window.
- No media extraction/export or chatbox subtitles. Streaming uses normal browser buffering/cache.
- Provide a Windows volume-mixer shortcut and instructions: Edge audio must be routed separately from the Speech output selector.
- Stop YouTube, Stop speaking and panel/app closure stop only the owned player session, leaving ordinary Edge windows open.

### [1.20.0rc1](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.20.0rc1) — WAV / MP3, SRT and shortcut capture

- Add Soundboard recordings with local WAV/MP3 files, optional SRT captions, hotkeys and ±10-second subtitle offset.
- Support audio-only, audio + captions and silent subtitle playback; Stop cancels audio and future subtitles.
- Read common SRT encodings and overlapping/multiline cues. Rate-limit captions and keep their timeline aligned to playback.
- Fix shortcut recording with immediate single-chord capture. Suspend application shortcuts while editing and restore them on Save/Cancel/close, including nested recording settings.

### [1.19.0rc1](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.19.0rc1) — Multilingual Soundboard phrases

- Add up to 32 saved phrases, each with its own shortcut, language, provider, voice and text/voice/both output route.
- Add the Ctrl+; → ぽい (poi), Japanese, Polly Mizuki, voice-only example and punctuation hotkey support.
- Add editable rows, preview playback, persistence and conflict checks against Roleplay shortcuts. Preserve the main language/voice and unsent editor text.
- Saved phrases bypass translation, substitutions, random endings and personality effects.

### [1.18.0rc2](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.18.0rc2) — Audio crash fix

- Move device scanning into a disposable helper process to prevent concurrent PortAudio initialization/termination beside microphone capture.
- Keep the last device list and listener state after failed/timed-out scans, then retry. Log safe helper exit codes and retain reconnect behavior.

### [1.18.0rc1](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.18.0rc1) — Selected original-project updates

- Adapt catalogues from the original GitLab project: 86 recognition languages, 111 DeepL entries and 100 distinct Polly voice IDs, including Polish Ola Neural.
- Select the required Polly engine and use supported Neural SSML. Preserve Standard voices and explain unsupported Neural pitch/whisper combinations.
- Add beta-language request options for additional DeepL languages and stage-duration diagnostics without transcript/key logging.
- Document the shared baseline, imported commits and deferred experiments in [UPSTREAM_REVIEW.md](UPSTREAM_REVIEW.md). Offline Whisper recognition is not included.

### [1.17.0rc1](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.17.0rc1) — Pronunciation, history and random endings

- Add a speech-only pronunciation dictionary separate from nickname corrections.
- Keep the last 50 output attempts in session memory, with load-for-editing/repeat actions and completion/cancellation/failure status.
- Make whole settings categories collapsible and remember their state.
- Add custom random endings such as “, poi” or “, desu”, with a saved 0–100% frequency slider and one shared choice per utterance.

### [1.16.1rc2](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.16.1rc2) — Global hotkeys and saved UI/voices

- Enable global Windows shortcuts by default, migrate old focus-only defaults once, and show registration/conflict status.
- Initialize the Windows message queue before registration and replace reserved default F12 combinations.
- Remember voices per provider/language, fallback voices per language and pitch across restarts.
- Add responsive columns, wrapping descriptions and saved window size/maximized state.

### [1.16.0rc2](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.16.0rc2) — Conversation controls and recovery

- Add Stop speaking / cancel pending auto-send, editable transcript preview and a configurable auto-send delay.
- Protect unsent drafts and add quick recognition/output language switching, initially Polish/English.
- Add background/manual device refresh, requested microphone recovery and safe output-device disconnection handling without rerouting or automatic replay.

### [1.15.0rc2](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases/tag/v1.15.0rc2) — First public Deluxe build

- Add local Windows Speech with optional Polly fallback, manual pasted-text speech and optional external Piper support.
- Add nickname corrections and keyword-triggered chatbox text/emoji additions.
- Add personality presets, custom announcements, hotkeys and delivery modes.
- Add diagnostic logs, safer background output and a standalone Windows executable with own-key configuration.

## Original VRChat Speech Assistant history

The historical entries below come from the original project by **Amelien Deshams
(Nekosan)** and describe its releases through 1.14.0. Their original GitLab links
and content are preserved; they are not Deluxe release announcements.

### [1.14.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.13.2...v1.14.0) (2024-08-19)

#### 📔 Docs

* update README ([cb06d40](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/cb06d40febd0ec95ab33be35d65b4cdcab0015cf))
* update README ([e814e09](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/e814e09017f4945e6c4098fd8d54ab561a1a10b7))
* update sphinx docs ([eabc16c](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/eabc16ce2edf25cddf548ac881f4ea2770734c59))
* update sphinx docs ([b4c9e9a](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/b4c9e9a771b0997f6c4f73d587ec7054849760fd))
* update sphinx docs ([4d9d57d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/4d9d57dd87d1184a8bc96708f81bff56db8a274a))

#### 🦊 CI/CD

* **venv:** removed debug venv ([4202359](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/4202359a89337ad7ccdd296c79a852b34a0e94a2))

#### 🚀 Features

* voice pitch and clear chatbox text ([0e0a38b](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/0e0a38b829421820f6b46d8ba14514f20c205e65))
* **extra_tags:** added support for pitch extra tag ([182772d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/182772d8819ba6d479cf396ff97c1dca84d97e1e))
* **languages:** added Arabic language ([a9bf3b3](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/a9bf3b36beb9e4e6b9a6a801003320ce727a7c8b))

### [1.13.2](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.13.1...v1.13.2) (2024-05-07)


#### 🛠 Fixes

* **config_dialog:** fix missing parent window icon ([d2e28a6](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/d2e28a6a9a8c5496e499ee2e3c6740c9d6450b84))

### [1.13.1](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.13.0...v1.13.1) (2024-05-03)


#### :scissors: Refactor

* update pathlib default current directory access ([2981e3d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/2981e3d10198a4578e3048b272bddfe6697f7fe0))


#### 👀 Reverts

* fix RESOURCES_PATH changed previously with pathlib ([c460b8a](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/c460b8a6a66634d89c5405b9562b9e07ba9a684a))


#### 📔 Docs

* update docstrings ([46ad126](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/46ad1261af7c6b262c143e381f941f8974545078))
* update README ([fc1a3b9](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/fc1a3b94c57b616f47dac191b365d44e95be025c))
* update sphinx doc ([6f516bb](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/6f516bb08f926bac0086f683d0bbe082214968b5))
* update sphinx docs ([0d4cdce](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/0d4cdce6b3dfb08bb320ccc5c58353aadbc5f4c4))


#### 🦊 CI/CD

* fix CURRENT_DIR ([4c29d3d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/4c29d3d346d5ad4fba2329c567e11aff6081b0c7))

### [1.13.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.12.1...v1.13.0) (2024-05-03)


#### 📔 Docs

* update README ([35373b3](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/35373b33368a4f5e60ac7a889580a4e3e5ab09fb))


#### 🦊 CI/CD

* replaced SCRIPT_PATH to CURRENT_DIR ([aaab670](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/aaab6707d155f6981e07441ce6cb3793b8aa27f1))


#### 🚀 Features

* add __author__ and __email__ ([d2d98e8](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/d2d98e8c191734e36e7aca7c02fc79752c02a0d0))

### [1.12.1](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.12.0...v1.12.1) (2024-05-02)


#### 📔 Docs

* update LICENSE ([d6c96d3](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/d6c96d3fa1b79796110aaab03937b30170d4588d))
* update README ([bb4edc1](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/bb4edc1acefc112faf1081888c1220a9382d72c8))


#### 🦊 CI/CD

* update MANIFEST ([ff3bec6](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/ff3bec649b0941e88938fece1367e3942290b839))
* update .releaserc.yml ([13ebb14](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/13ebb1408ccde5e9d0bf5b698ebb6156b57e033e))


#### Other

* add .editorconfig ([3c6165c](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/3c6165c4427428f41aa69fd2d13019470d857ca9))

### [1.12.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.11.1...v1.12.0) (2024-04-20)


#### 📔 Docs

* update README ([36f7e83](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/36f7e837aa26683d6921e043234aecd75355206c))
* update sphinx doc ([6856030](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/6856030055ee07e17934c87dce08423605a90324))
* update sphinx doc ([1cd48f6](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/1cd48f6b0c12d72c805c3bb108fd0f289099a901))


#### 🚀 Features

* **devices:** extract the devices module into an another Gitlab repo ([e531614](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/e53161415041be8db81e4cf0c9f5c3a92186295b))

### [1.11.1](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.11.0...v1.11.1) (2024-3-2)


#### 📔 Docs

* update README ([498e043](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/498e0430d279fa6c3ac996cca2fe7a0401fbbaec))


#### 🛠 Fixes

* **VRCSpeechAssistantWindow:** typo fix in chunk length variable name ([bd1b987](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/bd1b9879332beda27e350041d50c433bfd76472c))

### [1.11.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.10.0...v1.11.0) (2024-2-20)


#### :scissors: Refactor

* removed deprecated refresh_devices method ([f32530f](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/f32530f40b82ae296b7db6f5902462c09dcc751b))
* **icons:** skip pylint ([bfb5846](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/bfb5846a73a1d2d48534ed29f951cc9707f4f6e5))


#### 📔 Docs

* update docstrings ([5735fec](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/5735fec9ff61d1eeb0138242e225de4d4e2098cb))
* update README ([702e864](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/702e8641a66bf126a5e606b9dcd9c44da445c190))
* update README ([0fbf972](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/0fbf9726632153578e67ba4809e942b8eb2d0330))
* update README ([dfa8896](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/dfa8896a5ed6c945f326e1cee5e25540687cc793))
* update README ([5e9c501](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/5e9c501d52a9bff3fef0087959444fe2ac86efc0))
* update resources ([3015684](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/3015684fd5cd86897a4d407696ff58d12d8797fe))
* update sphinx documentation ([18d78d4](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/18d78d4c41b9bd7723f2b92460cbe41e916aad35))
* **license:** update copyright year ([31201fe](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/31201fec6a6fc8a42adf2a403b689ac0df887159))
* **README:** include changelogs in README ([2641056](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/26410564ab813657ea851fced46f34a8fde15d13))


#### 🦊 CI/CD

* update dependencies ([1dcb80c](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/1dcb80c6f80ee692d57f57518265f25a1eb66782))
* **setup:** update author email ([b59810d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/b59810d6721c73ff87f66ae987aa992a6bfe4085))
* **setup:** update classifiers ([28fd082](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/28fd082b0624a8515faaef7b80a44f263e784e16))
* **setup:** update lowest python required version ([435cde7](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/435cde7f19589077f44d5b3d7035d380e9cc82b5))
* **setup:** update project_urls ([9c5714e](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/9c5714e47c5fdd065eeb0a32390893ef80d1a9f3))
* fix pipeline ([3d753bf](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/3d753bf95fd363e6cd7c70a0e115a3158754731a))
* update CI pipeline to use Python 3.11 ([c9d5f90](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/c9d5f907db9f8f3b6b74680b9d8b7ce6849193b2))
* update pipeline ([16e4257](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/16e425740093504c8ae4aef2674923b64c7eba0a))


#### 🚀 Features

* added Speech and Chatbox configuration to be expandable / collapsible ([eddbbb2](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/eddbbb2ccdbfd2700539822dfd9169f403b30436))
* update activation button and progressbar style ([0a5d30b](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/0a5d30b09812374246b9b79a6228bc9aeab2fffa))


#### 🛠 Fixes

* fixed configparser encoding ([5b2a021](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/5b2a0210ddde19bab0f2bef250bacf3e14bd8b5d))
* moved input device selection outside of the `speech` group ([dc466ea](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/dc466ea877d0b02ef2d584a50d89ded273b4184e))
* **devices:** correct host_api_name following device type is input or output ([3b83439](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/3b8343930075f3b4d0ab3cc1fd1ea80ac386bd9a))
* **devices:** using wrong HOST_API ([363bbb8](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/363bbb815020c47d038597d5122ed40a9d866e80))

### [1.10.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.9.0...v1.10.0) (2023-11-02)


#### 📔 Docs

* add auto-generated API docs using sphinx ([2be362e](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/2be362e1808bf25542bdbdaf27e7e59c6b0c65aa))
* update email ([1fbc27a](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/1fbc27a36bd20877ff571fa8e58646df28720666))


#### 🦊 CI/CD

* update Python version requirement ([a07c940](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/a07c9408cdedcdde4c02eb533591f981d04a4815))
* updated gitignore to exclude _config.py ([75f5cc4](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/75f5cc44fe34491e79afc824e8711684fe5d2c7b))
* added check-var stage ([109b472](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/109b472236039581cebb4a9e3a0c88575c9215e1))
* update gitlab templates ([e8e8b1d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/e8e8b1da81326a53bb25e7e38554767842c3bbdf))
* update pipeline ([edff637](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/edff63709489eb634d48f8429c392d1c266770c5))


#### 🚀 Features

* chatbox writing animation and font, updated config check for older versions compatibility and replaced sounddevices by PyAudio and Pygame for better performances. ([f3bd4cb](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/f3bd4cb761de7494bff5f86b39bc5b940ee06c57))


#### Other

* renamed version.py to _version.py ([443cf83](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/443cf83aae5a6459ca33914a1640c864887c12b3))

### [1.9.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.8.0...v1.9.0) (2023-10-30)


#### 📔 Docs

* update README ([9a71204](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/9a71204c1d9d442894f6a2493698a75f90b00055))


#### 🚀 Features

* **config:** Load defaults and overwrite with saved configuration to prevent new configuration variables from preventing launch. ([64ce059](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/64ce059aa3a7830f7a1d79efd23e773fa745e365))

### [1.8.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.7.0...v1.8.0) (2023-07-24)


#### ⏩ Performance

* removed dynamic energy threshold ([ffa5a51](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/ffa5a5133c95454380ca66a1733750874eeb1828))


#### 📔 Docs

* update download link ([9ffc79b](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/9ffc79b56c706cc3dfd00296bfaf27082480c8b9))
* update download link ([f5da108](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/f5da108ff5b1723a61b1d0bebfd7a1def9c8ea6f))


#### 🚀 Features

* added Japanese formality ([dfe626d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/dfe626d2af565857f418cb4a4b93afa61ea0cb9d))
* new UI sounds ([0570f75](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/0570f75a7659cdcd497ca91b4ffd6c31a741a4aa))

### [1.7.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.6.0...v1.7.0) (2023-06-21)


#### ⏩ Performance

* reset listener thread after every recognized text ([c60327a](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/c60327a52166f557a3a76783098cc4e75182f3ff))


#### 📔 Docs

* update LICENSE ([8ca597d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/8ca597d0a0e7e2bba0dccabdc52653be72eab557))


#### 🦊 CI/CD

* update classifiers ([ac47aef](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/ac47aefa0e084de37d74c44df818cb1d4494f4d8))
* update requirements versions ([4472352](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/4472352522731c7508b56007d64990ffa9c0297c))


#### 🚀 Features

* added more words to ignore ([22fa89e](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/22fa89e87266a7b1b133e6c47b8fca53c41e0a58))


#### Other

* removed python2 coding args ([09dc115](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/09dc1158af307dcf3b81251faa80b99733836f35))
* update pylint config ([b68ca7f](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/b68ca7fb14c93ed0a5522df01e30de25d528e041))

### [1.6.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.5.0...v1.6.0) (2023-05-05)


#### :scissors: Refactor

* separate functions in utils ([625bef2](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/625bef2d7bc4457c45a9892891644cda0f1218c6))


#### ⏩ Performance

* refactoring of the code for better performances ([5542938](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/5542938f5a4df2cb6fb98db2b4a3b7664f1d8300))


#### 📔 Docs

* udpate docs ([a5e4ecf](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/a5e4ecf7f0ab2d58c78b57ec4fc02a6567c99e4d))
* update README ([479b144](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/479b1447efa9a50c0d25c2686d13a64159b2e6fd))
* update README ([79e506b](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/79e506b519e2bc55994fbd7edf9c1c0743e8a6fa))
* update README ([dcb1b6d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/dcb1b6d359c4f28fd61476b4ad28825217756c3e))
* update README ([94949ea](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/94949ea775f3a5aa20737168bf451d380f7131a7))
* update README ([c759e6f](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/c759e6f6159d60828f47e7a282928db0bc8cfc54))


#### 🚀 Features

* add osc server to listen commands ([2adda2a](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/2adda2a15f753c71a6c6bba18ba019878d3e6a58))
* added Korean and Norwegian language support. ([fc06239](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/fc062393a3e1fabfc758c2eb3a030ebf1e7633c8))
* hide DeepL free api key and tests using get_usage method ([021fa70](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/021fa70188f031df538130af0b9f5ca2fac3d243))
* toggle recognizer beep sound ([73b6833](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/73b6833e2891ddc2c2c0d48d4b20b971cb7ed127))
* update pause_threshold and non_speaking_duration values ([547f874](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/547f87430638c95e21adf5ba5b5a8cd951d136e7))
* voice activity bar ([62d2126](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/62d21264f21f3792dc9bd28926821db083a2057c))


#### 🛠 Fixes

* auto refresh devices on open if config mismatch ([14eb9a6](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/14eb9a6367a21bd0cdbe81207a67ae004c9ab5f1))
* ignore space for server receving osc message ([020655d](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/020655d9e06605df0c763e0d63546fffc78c98e1))
* refactoring of the management of audio devices ([d187c63](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/d187c638a7064cebb3532be3288429297ecc44b4))

### [1.5.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.4.0...v1.5.0) (2023-02-08)


#### 📔 Docs

* update link ([0cc2491](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/0cc2491516c3f1e5a55efb5378f2a2e6f4fd6d50))


#### 🦊 CI/CD

* update note. ([7a4bfdc](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/7a4bfdc311bff340eb676f5e09dd1bcd1b2e0e91))


#### 🚀 Features

* add extra tags and refresh devices. ([bd7e785](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/bd7e785ba16ea89a8c77a314575c6e5d8c47c394))

### [1.4.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.3.2...v1.4.0) (2022-10-07)


#### 📔 Docs

* update doc ([e663cbc](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/e663cbc41f21e2b5d47bb91e26af7c56b9b1f576))
* update doc ([d85dd35](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/d85dd355dcdf166c4ad0bff3b80a5932e965b0db))
* update download link ([36a2112](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/36a21123bf85497e070add30b6d1fe04a326673f))


#### 🚀 Features

* added Ukrainian language support. ([07067c8](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/07067c878f505020229bee0303bac6d100cb5ca3))
* Replaced beep sound and typing animation. ([f249666](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/f2496667def011612ca04f80016441a72e50b8be))


#### 🛠 Fixes

* disable trying to speech if there is no voice available for the speech. ([2bdffa9](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/2bdffa9b39a6cf6faef6cdad1416e0d9cef9f083))
* update free deepl api default key ([3b13b94](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/3b13b94a2401ba87b233a42b9c09d29f72a12cc2))
* wrong english Deepl source language attribute ([54fd9af](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/54fd9afcbd84c34323489e568ef28a0071c831cd))
* wrong english Deepl source language attribute (formality) ([5934eb4](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/5934eb4eb5a31ab1369a9659f9423ada71164c20))

### [1.3.2](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.3.1...v1.3.2) (2022-09-16)


#### 📔 Docs

* correct spelling ([eec88d0](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/eec88d08bfaa5fbc5ac25b6269fd550fc20da646))
* update download link ([9851e40](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/9851e40f7dd708d9f9802b669c4566665a45717c))


#### 🦊 CI/CD

* restore .pylintrc file ([3680110](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/368011032e15765ee271e833597e892fdbf76710))

### [1.3.1](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.3.0...v1.3.1) (2022-09-16)


#### :scissors: Refactor

* correction of spelling errors ([38aac46](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/38aac46d9bb273f555733adc521a23b0f829f922))
* removal of unnecessary brackets ([4d502ce](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/4d502ce6c324c2bbb7c7bcd38f499ad91d8ab779))
* removed argument equals to the default parameter value ([f72a565](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/f72a5656db8e3e2e096bc6d85b3d1d7131162f8f))
* renaming of various variables ([fe3268b](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/fe3268ba230c4a636e9b7f33553ef0a94c8cbe0c))
* replaced atom badge with Pycharm ([b3db13e](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/b3db13e6ca9e72783394da910921fc94886037ab))


#### 💈 Style

* replaced description line too long ([069ecef](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/069ecef077a26372c7462e1904d2e51f9703f474))


#### 📔 Docs

* refactor docs ([58303c3](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/58303c332fe356cfa467111e8d8288cc1ecb7b42))


#### 🦊 CI/CD

* removed pylintrc file ([1081a35](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/1081a35aeebb7d5fd30b9246dc15c80043939ea9))

### [1.3.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.2.0...v1.3.0) (2022-09-02)


#### 📔 Docs

* add README documentation ([ef85177](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/ef8517771fae3065c332ef92fa88351c0d071236))


#### 🚀 Features

* add free API keys ([e9e0f47](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/e9e0f4721a9fdabecc864913f6caf75047488aaf))

### [1.2.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.1.0...v1.2.0) (2022-08-31)


#### :scissors: Refactor

* reformat code ([0f7c505](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/0f7c505580e6ea042965494898a984e707592f21))
* rename Portuguese Brazilian for using with args ([0c58c4f](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/0c58c4fe8b9017c595e9ed67327914a314b0880e))
* update recognizer beep ([67f9754](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/67f975424b4fa99e37236192931c618ccf243cd7))


#### ⏩ Performance

* perf and tests improvement ([311975a](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/311975af695866734ee7432722855ba272d2c72f))


#### 💈 Style

* add SCRIPT_PATH constant ([8cffced](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/8cffced9b0496aa2d5068880ea8c0ee6aa02732a))
* isort ([a0c6854](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/a0c68543204ea62c1659f82ff882612b79f22126))
* refactor ([3258c86](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/3258c8684e8f75b537590213ff1ae870ff82dd67))


#### 🚀 Features

* add formality argument parametter ([361eb0c](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/361eb0c46bac2dcc472b7faaf29778300750ff6a))


#### 🛠 Fixes

* Formality ([eacf9b2](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/eacf9b2cb14eacda1b797a00cf115e21cb2c6632))
* formality was not saved in ui ([2dd5561](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/2dd55617ffab2cb5e2566f49213da28119bc5875))
* Portuguese Brazilian renamed ([6c46c81](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/6c46c817263de318ed7e1e43228e8d929f7d4199))
* when saying stop send OSC typing False ([657ec25](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/657ec25347ff1859c606bb14a16c67292a817cfc))
* wrong formality parameter in basic configuration ([7da01b0](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/7da01b07de768f70cb1b3f2978126059c52def19))
* wrong language key for Japanese ([67e4631](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/67e4631f9260b31573fa8df21a56714c276b5550))

### [1.1.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.0.1...v1.1.0) (2022-08-28)


#### :scissors: Refactor

* change log label widget color to orange ([ef1d1cb](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/ef1d1cb98260134fc721bcf38c9119e7bd033c63))
* reformat ([9a63039](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/9a6303976f7755a369b8e52df92f486721da2d31))
* set log level to INFO ([8eebce8](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/8eebce8e05dbf550758ffc5fe018ee2cc6e850f5))
* update log info "Listening" ([a85bfa2](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/a85bfa289dc5281d06ec2ce44d270b9f7cb13140))
* update log level info to warn ([784840c](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/784840c6fbea850189867789dc7e422ffcb70dc3))


#### 🚀 Features

* add mic source input ([3ba7604](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/3ba76041224bd09b90660578db8d0c291d54f4ca))
* add on voice combo clicked ([aa12509](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/aa1250966cee96158483d470fdeafd0e6f0a044e))
* add tips label under the banner ([d7b457e](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/d7b457e8c27974cca9a3be4adbab6adc0d557850))
* add translator formality widget ([d779c87](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/d779c872b3e422c0dbc5dd0771ba1cc92211f9c8))
* set fixed size ([42751e2](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/42751e2bb743a268940ae89ecdc82d227ecda129))
* update args parser ([98709a0](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/98709a07f23bc79e28d2d92442bc80d0da70a81c))


#### 🛠 Fixes

* remove margin top for groupbox ([777e5fc](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/777e5fc6b8a176b5885ec3c74dd1ea42e3ded174))
* update open repo link ([6c9a6fc](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/6c9a6fc8ff29526e7a984b5904535a83f4a95284))

### [1.0.1](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/v1.0.0...v1.0.1) (2022-08-26)


#### 🛠 Fixes

* add MANIFEST file ([c1004d6](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/c1004d62abf0c37223f1ef79bb38703612517c71))
* wrong key ([eda0fe6](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/eda0fe65937dade8967bd05544325ab3fac5d06c))

### [1.0.0](https://gitlab.com/ameliend/vrchat-speech-assistant/compare/...v1.0.0) (2022-08-26)


#### 🚀 Features

* append logo ico ([9232d29](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/9232d291458b888a804fad1e6f4b661e33de52e2))
* initial commit ([18a9001](https://gitlab.com/ameliend/vrchat-speech-assistant/commit/18a9001b9b1d1b783ef1a130b3be9f454dec322d))
