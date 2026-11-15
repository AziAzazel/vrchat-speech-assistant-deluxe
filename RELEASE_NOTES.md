VRChat Speech Assistant Deluxe 1.30.0 release candidate 1

A persistent bottom status bar stays visible while scrolling through settings.
See listening/off, recognition, auto-send countdown, draft pauses, output and
cancellation, device scans and microphone recovery from one place.

Warnings and errors remain until dismissed. Informational messages do not hide
them. Errors take priority; hover for full notice details. Dismissal acknowledges
a notice rather than fixing the cause. Notices are session-only.

Dropdowns and sliders no longer change values with the mouse wheel, even when
focused. Wheel gestures scroll the surrounding settings panel/table instead;
mouse and keyboard editing still work, as does scrolling an open dropdown list.
This applies to the main window, Roleplay, Soundboard and recording settings.

Available for Windows and Linux. Replace the old application files; your settings
remain in the user folder. Regression tests cover footer visibility, persistent
issues, recognition cancellation, preview/output lifecycle and wheel behavior.
Both packaged builds also verify that the footer remains outside the scrolling
area and retains a warning after an informational message.
