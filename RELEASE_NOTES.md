VRChat Speech Assistant Deluxe 1.26.0 release candidate 3

Favorite reactions on large buttons
- Mark Favorite ★ in Roleplay → Soundboard phrases and hotkeys, then Save.
- Buttons retain each row's language, voice, route, whisper, pitch and independent
  chatbox text; recordings retain their audio/SRT settings. A hotkey is optional.
- Add up to six starter reactions once when the output language is Polish or
  English, using the current provider/voice. Polish: Tak, Nie, Chodź, Poczekaj,
  Nie rozumiem, Powtórz. Existing rows and the 32-entry limit are preserved.
- Buttons reflow with the window, pause during output and preserve unsent drafts.

Chatbox page preview
- Preview pages while typing, with Previous/Next, a page counter and VRChat limit.
- Use the same font formatting and Unicode-aware splitter as actual OSC output.
- Update to final pages after translation/random additions, without overwriting
  a newer editor draft. Preview itself sends no text and performs no synthesis.

Separate display text in the main editor
- Enable Use separate Chatbox text and type an action/emoji in the second editor.
  Enable Send manual text to Chatbox as well; edited recognition uses the main
  Chatbox toggle. The voice can say a sentence while text shows *looks suspicious*.
- Display text is not spoken, translated or decorated with keyword/personality
  additions; the selected font applies. Blank uses the normal message.
- Editing pauses auto-send. History Repeat retains separate text; a fresh
  recognition preview clears the previous action to prevent accidental reuse.

Responsive columns now follow the visible scroll viewport, avoiding oversized
three-column layouts on Windows and allowing the window to shrink again.

Also retain saved local voice choices when the backend/model is temporarily
unavailable, so editing another Soundboard row does not erase those choices.
Playback still checks availability.

Download VRChatSpeechAssistantDeluxe.exe (Windows x64) and replace the old file.
Settings remain. Editor/action text and history remain session-only.
Validation covers routing, Unicode pages, final/stale preview updates, auto-send
pause, favorite persistence/capacity, busy state and draft preservation, plus
packaged Windows controls. Real voice/device routing and VRChat font rendering
still depend on the user's configured hardware/services.
