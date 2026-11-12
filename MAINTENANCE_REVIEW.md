# Maintenance and performance review — Deluxe 1.22

Reviewed the runtime modules, packaging, dependency declarations, event handlers,
settings persistence and resource lifetimes against release `v1.21.0rc4`.
No speech backend, roleplay feature, language/voice choice, hotkey, Soundboard,
SRT mode or YouTube control was intentionally removed. Config paths and keys are
compatible; unused legacy keys remain readable. MIT attribution is preserved.

## Changes with a concrete benefit

| Area | Before | Result |
| --- | --- | --- |
| SRT | Full cue scan and string creation on every 20 ms tick | Advance through sorted boundary events; reuse text between changes; rebuild on rewind. Same overlap order and 144-character limit. |
| Settings | Rewrite config.ini for each save callback | Skip unchanged writes; batch startup/language updates; atomic same-directory replacement; report I/O failure while preserving the previous file. |
| Sliders | Disk write for every drag position | Live in-memory pitch/frequency with persistence on release; keyboard/programmatic changes still save immediately. |
| Polly | Construct/validate clients on repeated voice/provider changes | One locked client cache per window, keyed by credentials/region; validate successfully once per key; retry failed checks. Never log credentials. |
| SDK loading | Import cloud SDKs and pygame during local startup | Lazy imports when the corresponding backend is used. First use still pays its initialization cost. |
| Audio scanner | Two PortAudio contexts and two full enumerations per scan | One context/enumeration supplies both directions. Still a disposable child process; failed scans preserve the last list. |
| Resource ownership | Global OSC dispatcher could retain old window callbacks; hidden YouTube panel kept a timer | Per-window dispatcher and timer stopped on panel close. |
| Packaging | Full botocore service-model tree | Keep Polly, common endpoints/partitions/retry/default metadata and TLS roots. About 17.5 MB of unused model data excluded before compression; source SDK unchanged. |

## Removed clutter

- Direct `logger` and `pyaudio-devices` VCS requirements: runtime uses standard
  logging and its own isolated PortAudio scanner. Transitive dependencies, if any,
  remain the responsibility of their owning packages.
- Four unreachable private methods from superseded UI/API handling, unused imports
  and obsolete layout constants. The icons import is retained because it registers
  stylesheet resources; `__version__` remains an intentional public export.
- 157 generated HTML/cache/documentation files, approximately 4.87 MB in the
  working tree. Documentation sources and build instructions remain; this does not
  remove Git history or directly shrink the executable.
- Inactive inherited GitLab release pipeline/configuration; GitHub Actions is the
  active Windows release pipeline. Project metadata/contributor links now identify
  this fork. Original provenance/license/review records remain intact.

## Measurements

Shared Linux environment, Python 3.12. Timings vary with load and cache state.
Run from the repository with the development environment:

```sh
PYTHONPATH=src python scripts/benchmark_runtime.py --baseline-ref v1.21.0rc4
```

The script compares identical subtitle results, includes index construction, and
uses fresh subprocesses for imports. It uses synthetic settings/captions and fake
configuration only; it never contacts AWS/DeepL or reads the user's private config.

Latest local medians of three runs:

| Component | Reference | Updated |
| --- | ---: | ---: |
| 4,000 cues / 3,000 subtitle positions | 2.4814 s full scans | 0.0147 s indexed, including construction |
| Provider module import in fresh Python | 0.8137 s | 0.1168 s; boto3 absent until needed |
| 200 identical save requests | 200 writes in the former writer | 1 write |
| 100 changed values inside one batch | 100 writes without batching | 1 write |

A separate headless GUI check with simulated audio providers measured startup
settings writes decreasing from 2 to 1 and a language switch from 3 to 1.
Subtitle timing speedups varied across local runs (roughly 80–170x); these are
lookup costs, **not whole-program speedups**. No whole-app RAM/FPS/startup claim
is made. PyInstaller extraction, Qt/SAPI/device startup, first cloud validation,
network latency, Piper models and browser playback have independent costs.

## Verification and boundaries

Regression checks cover existing features plus exact indexed/reference cue output
across overlap/gaps/rewind, write deduplication and failed atomic replacement,
slider persistence, isolated single-context audio scans, dispatcher ownership,
concurrent client reuse, deferred SDK imports and the reduced bundle's required
models/certificates. Windows packaging checks still exercise the real GUI, SAPI,
worker WAV/MP3 playback, SRT output, global shortcuts and owned Edge lifecycle.
The packaged test also constructs an actual Polly SDK client with fake explicit
keys, without an AWS request, to check lazy imports and bundled models.

Initial cloud credential validation remains synchronous; repeated successful
checks are cached. Automatic audio-probe cadence stays at five seconds to retain
recovery responsiveness. Generated audio caches are not silently deleted or
converted, since that could trigger new cloud synthesis/costs. Real AWS/DeepL,
user audio hardware and live VRChat/YouTube routing remain user-dependent checks.
