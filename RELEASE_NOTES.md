VRChat Speech Assistant Deluxe 1.23.0 release candidate 1

Fix: chatbox text no longer waits for the whole synthesized utterance to finish.
- Publish the first complete page before synthesis/playback.
- Format once and split long text into readable VRChat-sized pages, with UTF-16
  limits for emoji/styled letters, word boundaries and long-word/CJK handling.
- Advance pages during audio using playback position/duration; approximate page
  alignment, not word-level timestamps. No unseen page is silently skipped.
- Keep one synthesis/audio clip per utterance, preserving voice, pitch, delivery,
  pronunciation, translations and avoiding extra per-page Polly requests.
- Text-only pages have reading time; very fast audio can leave remaining pages
  afterward instead of discarding them. Minimum update interval is 1.5 seconds.
- Disable the legacy typewriter animation that delayed chatbox output.
- Stop cancels future pages promptly and leaves already visible text in place.
  Chatbox errors are reported separately from audio/device failures.

Editable preview and its configured countdown remain in effect. Recognition and
translation must first produce the accepted text; Google still returns completed
fragments, not live partial word-by-word transcripts. SRT/YouTube are unaffected.

Download VRChatSpeechAssistantDeluxe.exe (Windows x64) and replace the old file.
Existing settings remain, with only obsolete typing animation disabled.
Validation includes ordering before blocked speech, long-message completeness,
UTF-16 pages, timed updates and cancellation, plus packaged Windows WAV/OGG tests
that assert the second page is delivered while real audio playback is active.
VRChat reception and real audio-device latency require user hardware testing.
