# Live Voice Studio (experimental offline DSP)

[README](../README.md) · [User guide](USAGE.md) · [Development](DEVELOPMENT.md)

Live Voice Studio processes microphone samples directly. It does **not** turn
speech into text and synthesize another voice. Speaking rhythm, laughter and
expression remain in the audio. The built-in DSP needs no account, Internet,
AWS, CUDA or GPU; it can run beside VRChat on an AMD system.

## First setup

1. Open **Live Voice Studio**, wait for the device scan, and choose your physical
   microphone. Device choices include the host API; on Windows try WASAPI first.
2. Choose **CABLE Input** (VB-CABLE playback endpoint) as Studio output. Choose
   **CABLE Output** as VRChat's microphone. Other virtual cables work the same way.
   On Linux use the existing **Linux virtual microphone / routing** helper and
   your PulseAudio/PipeWire recording/playback routes. Studio enumerates PortAudio
   devices separately from the older SDL TTS output selector.
3. Start with **Microphone**, **48000 Hz**, **256 samples**, **Low Latency** or
   **Balanced**, and **Mono (VRChat)**. Mono is downmixed before playback and
   duplicated if the physical endpoint requires stereo. Devices supporting only
   44.1 kHz can use **44100**. Stop Studio before changing devices/audio format.
4. Switch **Live Voice Changer ON**. This is independent of the existing
   **START LISTENING** speech-recognition button; recognition is unnecessary here.
5. Select **Natural**, then **Vocaloid**, **Anime Girl**, **Robot**, etc. Presets
   change the actual DSP, without reopening the microphone/output streams.
6. For listening, choose a **different** monitor endpoint (headphones) under
   **Audio format, monitoring & microphone controls** and enable **Monitor Voice**.
   Do not route the cable's capture endpoint back into itself.

The app does not install drivers, change system defaults or configure VRChat's
device selection. Pick explicit endpoints; disconnected/renamed devices are not
silently replaced with another microphone or speaker. Ordinary device errors retry
the same saved endpoints. A native driver crash ends only the isolated audio
worker; switch ON again after correcting the device. A missing monitor can fail
independently while the main VRChat output continues.

## Effects and presets

The main effects are independent **Pitch Shift** and **Formant Shift** (−12…+12
semitones), actual **Auto-Tune**, **Vocoder**, and up to four harmony voices.
Changing pitch with formant at zero preserves the estimated vocal-tract envelope;
the separate formant control changes that envelope without changing F0. This is
cepstral DSP, not a trained character voice model.

Auto-Tune uses confidence-gated YIN F0 detection (approximately 65–1100 Hz), then
quantizes to the nearest allowed note. Choose C–B and Chromatic, Major, Minor,
Pentatonic, Harmonic Minor, or Custom notes. Unvoiced/noisy blocks are not forced
onto a note. Strength, Retune Speed, Humanize and Pitch Smoothing control the
correction; **Hard Tune** overrides Retune Speed, whose control becomes disabled.
The monitor displays detected F0 and input/target notes. Detection uses a 2048-sample
lookback; a zero retune setting does not eliminate the analysis/audio buffering.

Vocoder carriers are Saw, Square, Synth and Noise, with 8–64 bands and a wet mix.
Harmonizer modes include octaves, thirds, fifth, major/minor chords, choir and
Custom. Each voice has pitch, formant, level, pan, delay and detune controls.
Spatial effects are retained for stereo monitoring; the VRChat mono option
downmixes the final bus.

**Advanced Effects** contains individually expandable controls for input/output
gain (−24…+24 dB), gate, adaptive spectral noise reduction, vibrato, chorus,
distortion, bitcrusher, glitch, reverb, delay, three-band EQ, compressor and
limiter. Each module has its own enable switch. Drag the processing-order list
to reorder modules. The final output safety ceiling remains enforced regardless
of order. Disabled effects do not run their DSP; re-enabled delay/FFT stages are
cleared/reseeded rather than replaying stale audio.

The 14 supplied presets include Vocaloid, Anime Girl/Boy, Teto/Miku Inspired,
Cyberpunk, Robot, Daft Punk/GLaDOS Inspired, Demon, Chiptune, Broken Vocaloid and
Harmonizer. These are **DSP stylizations, not guaranteed copies of character
voices**. Broken Vocaloid uses granular glitch, random octave-like grain changes
and bitcrushing; harmony presets add real parallel pitch-shifted voices.

Use **Save As**, **Duplicate**, **Save**, **Delete**, **Reset**, favorites and
**Import/Export** to manage your own presets. Built-ins remain available;
Reset reloads the selected saved preset. JSON files use schema version 1, are
limited to 1 MB, and contain parameters rather than executable plugins/models.
Settings live in `live-voice-studio.json` beside the existing app settings.
Routes and the working patch survive restarts; the microphone engine starts OFF
until you explicitly switch it on. Invalid settings are backed up before defaults
are used; saving is blocked if the original cannot be preserved.

## Monitoring, recording, TTS and shortcuts

Input/output meters, waveform, mic activity, clipping, F0/notes, processing time,
reported total latency and DSP load update from the worker. Sustained input/output
clipping can trigger an automatic panic mute. Keep monitoring on headphones;
software cannot identify every feedback loop created in external mixers.

- **Bypass** skips effects with a short anti-click transition; safety limiting
  remains. **Mute microphone** and **Push-to-Talk** affect only the mic source.
- **PANIC** mutes the entire Studio output, including TTS/monitoring, drops queued
  TTS and clears processing tails. Use **Resume output** after fixing the route.
- **Test Recording** captures the processed stereo bus for up to ten seconds.
  Save it as WAV or audition it on the separate monitor endpoint; audition does
  not replay into VRChat. Session audio is removed when Studio closes.
- **TTS** and **Both** can send existing generated speech/recordings through the
  same bus. Both mixes the mic and TTS before effects. For offline TTS choose
  Windows Speech or an installed Piper backend/model. Existing optional Polly
  synthesis still needs your credentials; Studio processing itself never calls it.
  Clips are bounded to 32 MB/five minutes. Stop speaking cancels its queued source;
  Panic also removes effects tails and mutes the whole live bus.
- Existing Voice pitch/delivery effects run before Studio when routing TTS. Set
  the older pitch slider to zero if you want only Studio pitch. Existing History
  export retains the generated source clip; **Test Recording** exports the actual
  mixed/processed Studio bus.

Configure Studio action shortcuts in **Roleplay → Personality, delivery and
hotkeys**: enable, bypass, monitor, mic mute, next/previous preset, held PTT and
panic. Assign an individual preset's shortcut from its Studio panel. They share
the existing conflict registry, and shortcuts are paused in the shortcut editor.
On Windows, enable the app's global-hotkey setting for use while VRChat is focused;
held PTT releases when its key or required modifiers are released.

On Linux, app-focused shortcuts work directly. Desktop/Wayland global shortcuts
still use external desktop bindings or OSC; a held PTT binding must send both
`--action studio_ptt` and `--action studio_ptt_release`. No system-wide keyboard
hook is installed. Existing local OSC port 7001 accepts `/roleplay` Studio actions
and `/studio/preset` with a name/ID; `/studio/effect` accepts effect, parameter,
numeric value (for example `pitch`, `semitones`, `7`, or `tune`, `enabled`, `1`).

## Latency, tests and scope

At 48 kHz the FFT windows are 21.3 ms (Low Latency), 42.7 ms (Balanced) and
85.3 ms (High Quality). Adjacent tune → pitch → vocoder share one window.
Separate spectral stages, noise reduction and harmony add their own delay.
Buffers of 64, 128, 256, 512, 1024 and 2048 are selectable; support and stability
depend on the actual device. Increase the buffer or disable unused stages if DSP
load/overruns rise, particularly while VRChat is consuming CPU time.

The displayed DSP block time is measured. Total latency is an **estimate** from
algorithm delay, buffer size and driver-reported input/output latency; it is not
a physical mic-to-headphone round-trip measurement. The Linux test sends a real
synthetic microphone through PortAudio and captures a separate PulseAudio output:
220 Hz → approximately 440 Hz, hard tune 450 Hz → 440 Hz, live changes keeping the
worker PID, exact panic silence, TTS routing and processed recording. Its JSON
report accompanies Linux release assets. This environment measured about 1 ms DSP
p95 and roughly 37–48 ms reported total for that Low Latency/256-sample test;
these are not measurements of your PC under VR load.

Windows/Linux builds run numerical DSP and GUI/preset/isolated-worker checks.
Linux also tests real virtual-device routing. Physical Windows VB-CABLE/microphone,
headphones, reconnection on your devices, listening quality and performance while
running VRChat require target-hardware verification. No CUDA assumption is made.

The implemented release covers **MVP, Vocaloid Engine and Advanced Effects**.
Optional **RVC/AI conversion, AMD DirectML and VST3 hosting are unavailable**;
there are no working-looking controls or automatic model downloads for them.

## Development and licenses

Use Python 3.12, install the project's constrained dependencies, and run pytest.
The new numerical dependencies are NumPy and SciPy (BSD licenses); SoundFile is
BSD-licensed and ships libsndfile under its own license. Their installed license
texts and source/project references are included in third-party notices. No GPL
DSP host or voice-conversion engine was integrated or silently relicensed.

`live_settings.py` owns the schema/presets; `live_dsp.py` owns stateful processing;
`live_worker.py` owns PortAudio; `live_controller.py` owns authenticated loopback
IPC and worker lifecycle; `live_studio.py` owns Qt controls. Worker settings are
atomic snapshots, control updates are throttled during dragging, and Qt polls no
audio data. Audio uses blocking PortAudio streams on its own worker thread, not
Python audio callbacks, so callback code contains no allocation/locking/disk IO.
Monitoring uses a bounded separate queue; native audio failures stay outside Qt.

Hidden `--live-voice-probe <report>` and `--live-voice-worker <port>` entry points
also work in both frozen executables. The latter requires the parent-created
session token and temp directory, rather than exposing an unauthenticated audio
control server. Normal users start Studio from its tab.
