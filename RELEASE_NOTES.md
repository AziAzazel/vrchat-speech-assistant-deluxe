# VRChat Speech Assistant Deluxe 1.32.0rc2

Polly Standard now prefers SSML pitch from −50% through +50%. Outside that range, the whole shift uses local processing. Neural, Windows Speech and Piper always use local pitch. The methods are never stacked, and audio export retains the final sound.

The slider marks SSML blue and local processing orange, with a value and SSML/Local/Natural label. Neural/local voices show an entirely orange track. A 0% button, double-click reset, zero marker and drag snapping make the natural pitch easy to select; keyboard edits retain 1% precision. Soundboard pitch colors follow the same rules.

Windows and Linux release assets are published together after their tests and packaged GUI/audio checks pass. Live AWS synthesis and physical microphone/VRChat routing still need account/hardware validation.
