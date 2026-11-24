# VRChat Speech Assistant Deluxe 1.33.0rc1

Live Voice Studio adds direct offline microphone processing: independent pitch/formant, real hard Auto-Tune with scales/custom notes, vocoder, four harmony voices, 14 editable presets, monitoring, PTT and Panic. Advanced effects include gain/gate/reduction, vibrato, chorus, distortion, bitcrusher, glitch, reverb/delay, EQ, compression and limiting. Parameters update live without restarting audio streams.

Optional TTS/Both routing shares the same DSP bus. Test Recording exports the processed bus; existing TTS/History behavior is preserved when Studio is off. Studio starts OFF and remembers routes/parameters. Windows global shortcuts and local OSC reuse the existing conflict registry; Linux global bindings remain desktop-managed.

Read docs/LIVE_VOICE_STUDIO.md for setup with VB-CABLE/PulseAudio, monitoring, latency modes and the test matrix. DSP time is measured; displayed total latency is driver/algorithm-based, not a physical round-trip guarantee. Real Linux routing measurements are in live-studio-report.json.

This is an experimental DSP release. Physical Windows microphone/VB-CABLE, headset listening and performance under VRChat still need target-hardware verification. Character-inspired presets are stylizations, not cloned voices. Optional RVC/AI, AMD DirectML and VST3 hosting are not implemented or loaded.
