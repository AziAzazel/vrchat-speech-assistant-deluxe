# Development and validation

[README](../README.md) · [User guide](USAGE.md) · [Changelog](../CHANGELOG.md)

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

## Maintenance notes

The current pipeline is [GitHub Actions](../.github/workflows/windows-release.yml).
See [the maintenance review](../MAINTENANCE_REVIEW.md) for reproducible component
measurements and packaging details, [the upstream review](../UPSTREAM_REVIEW.md)
for imported changes, and [the Sphinx guide](README.md) for API documentation.
The full user-facing release history belongs in [CHANGELOG.md](../CHANGELOG.md);
`RELEASE_NOTES.md` supplies notes for the next tagged executable build.
