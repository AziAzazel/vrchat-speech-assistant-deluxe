# VRChat Speech Assistant Deluxe

<p align="center">
  <img src="./Logo%20VR%20Chat%20Speech%20Assistant%20Deluxe.png" alt="VRChat Speech Assistant Deluxe — official project logo" width="420">
</p>

**[Download Windows / Linux](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases)** · **[Changelog / Historia zmian](CHANGELOG.md)** · **[User guide](docs/USAGE.md)**

Speak through your microphone or type/paste a message, then let a selected
computer voice say it in VRChat. Optionally show the text above your avatar,
translate it, or use roleplay phrases and recordings.

VRChat Speech Assistant Deluxe is based on [VRChat Speech Assistant](https://gitlab.com/ameliend/vrchat-speech-assistant), originally developed by **Amelien Deshams (Nekosan)**.

This is vibe-coded but works better than the original in my opinion. If there are any bugs let me know!

## What it does

- Microphone recognition and manual text-to-speech, including pasted ChatGPT answers.
- Local Windows desktop voices, optional external Piper, and Amazon Polly with optional fallback.
- DeepL translation, nickname corrections and a speech-only pronunciation dictionary.
- Chatbox text before speech starts, with paged preview and separate display text.
- Global hotkeys, editable transcript preview, language switching and Stop speaking.
- Roleplay personalities/delivery, random endings, emoji rules and session history.
- Large favorite-reaction buttons, Soundboard phrases and WAV/MP3 with timed SRT captions.
- A dedicated YouTube player in Microsoft Edge, without chatbox captions or media export.

Recognition still uses Google online. Windows/Piper synthesis can run locally;
DeepL and Polly require your own credentials. No shared API keys are included.
Built-in AI answers and singing synthesis are not implemented.

Linux x86-64 / Bazzite: download the portable `.tar.gz` and follow the **[Linux guide](docs/LINUX.md)**. Piper/Polly are supported; Windows desktop voices remain Windows-only.

## Quick start

1. Download `VRChatSpeechAssistantDeluxe.exe` from **[Releases](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/releases)** and run it on Windows x64. No Python is needed for the standard executable.
2. Choose your microphone, language, speech provider and matching voice.
3. For voice in VRChat, install [VB-CABLE](https://vb-audio.com/Cable/) or use your existing virtual audio setup. Select **CABLE Input** as Deluxe output and **CABLE Output** as VRChat microphone.
4. Enable OSC in VRChat and **VRChat Chatbox** in Deluxe for text. For pasted messages, also enable the separate manual Chatbox option.
5. Configure AWS/DeepL keys only if using those services. Piper needs its own executable and voice model. YouTube needs Edge and separate Windows volume-mixer routing.

Settings are created automatically in `%APPDATA%/VRChat Speech Assistant` and
survive replacing the executable. Keep `config.ini` private if it contains keys.
If transcript preview is enabled, its countdown still runs before output; reduce
the delay or disable preview for immediate sending after recognition.

## Documentation and support

- **[Changelog / Historia zmian](CHANGELOG.md)** — all Deluxe updates, including the latest chatbox fix, plus preserved original-project history.
- **[User guide](docs/USAGE.md)** — voices, setup, hotkeys, roleplay, Soundboard, SRT, YouTube and diagnostic logs.
- **[Developer guide](docs/DEVELOPMENT.md)** — source setup, tests and Windows builds.
- [Maintenance review](MAINTENANCE_REVIEW.md) · [Upstream review](UPSTREAM_REVIEW.md) · [Contributing](CONTRIBUTING.md) · [MIT license](LICENSE).
- **[Report a problem or request a feature](https://github.com/AziAzazel/vrchat-speech-assistant-deluxe/issues)**. Logs can be opened from **File → Open diagnostic logs**; review them before sharing.

Release downloads include the executable, SHA256 checksums, third-party notices
and packaged smoke-test results. The executable is unsigned. See the changelog
for version-specific changes and the developer guide for validation limits.
