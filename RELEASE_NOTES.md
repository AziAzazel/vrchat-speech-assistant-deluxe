VRChat Speech Assistant Deluxe 1.22.0 release candidate 1

Maintenance and performance update; existing settings and features are preserved.
- Indexed SRT timing: update only at cue boundaries instead of scanning all cues
  every playback tick. Overlaps, offsets, gaps, rewind and cancellation retained.
- Atomic settings writes with deduplication and batches for startup/language
  switching. Pitch/ending sliders persist on release while updating live.
- Defer boto3/DeepL/pygame imports until needed. Reuse Polly clients and successful
  credential validation; close unused validation response streams.
- One PortAudio initialization and device enumeration per isolated probe, plus
  per-window OSC dispatchers and no polling in closed YouTube panels.
- Remove unused logger/pyaudio-devices direct dependencies, obsolete private UI
  methods, generated docs/build output and inactive GitLab release configuration.
- Smaller Windows package: only Polly models, shared AWS metadata and TLS roots
  are kept, excluding unused AWS service models. External Piper support stays.

MAINTENANCE_REVIEW.md and scripts/benchmark_runtime.py describe reproducible
component measurements and limits. They do not claim a whole-app FPS or startup
speedup. Cloud/network latency and real audio hardware still need user testing.

Download VRChatSpeechAssistantDeluxe.exe (Windows x64) and replace the old file.
Validation includes regression tests, failed-write recovery, indexed cue timing,
SDK lazy imports/client reuse, required AWS data files and the packaged Windows
GUI/SAPI/worker audio/hotkeys/Edge/SRT checks. A real Polly SDK client is created
with fake explicit credentials without contacting AWS.
