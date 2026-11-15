VRChat Speech Assistant Deluxe 1.29.0 release candidate 1

Save the last generated speech directly from session history: select the row
marked Available and click Save speech audio…. Export uses the original audio
without another synthesis or cloud request, preserving generated delivery settings.

Windows Speech/Piper save WAV; Polly saves OGG. No MP3 conversion is performed.
The complete generated file remains available even after Stop or playback failure.
One clip up to 32 MiB is kept in memory. New generated audio replaces it; text-only
attempts keep it. Clear history, eviction of its row, or closing the app removes it.

Available for Windows and Linux. Replace your application files; settings remain
in the user folder. Tests cover original bytes, temporary-file cleanup, bounded
retention, cancellation, history selection, export without resynthesis and atomic
save failures. Packaged checks verify WAV export and the history control on both
platforms; Windows also synthesizes a real SAPI clip before exporting it.
