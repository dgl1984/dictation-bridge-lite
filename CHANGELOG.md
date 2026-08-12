# Changelog

## 0.3.0 — 2026-08-12

- Separated Windows+H temporary Composition text from the committed editor text so provisional word fragments and spoken command words are no longer echoed.
- Left the finalized online phrase to NVDA and suppressed only an exact rapid duplicate during the short commit window.
- Suppressed rotating online dictation tips and routine Listening or Thinking status changes while preserving genuine errors.
- Removed the broad diagnostic event tracing used during development, restoring lightweight and responsive offline feedback.
- Added **NVDA menu > Tools > DictationBridge Lite** with the two Windows 10 commands confirmed in live testing: `ms-settings:privacy-speech` for online recognition settings and `control /name Microsoft.SpeechRecognition` for the legacy offline Control Panel.
- Added a checked **Speak dictated text** menu item synchronized with the existing assignable echo toggle.
- Delayed legacy correction-panel reading until Windows has time to populate the choices and allowed normal NVDA event processing to continue.
- Added speech for actionable legacy WSR feedback while silencing routine Listening, Off, and Sleeping changes.
- Documented that ordinary offline dictation is responsive, online dictation is cleaner but delayed until phrase finalization, and legacy correction-panel events remain unreliable with NVDA 2026.1.
- Expanded regression coverage for online composition, duplicate suppression, online hints, menu command targets, offline echo, and best-effort correction handling.
- Kept all six native binaries and the native source unchanged.

## 0.2.1 — 2026-08-12

- Delayed dictated-text speech until transient UI changes settle, preventing command and suggestion tooltips from suppressing the next echo.
- Raised dictated-text and deletion announcements to NVDA's immediate speech priority so they remain audible while transient UI is being reported.
- Added regression coverage for dictated text, line breaks, and deletions through the resilient announcement path.
- Added a focused editable-value-change fallback for legacy offline Windows Speech Recognition text that bypasses both TSF and NVDA typed-character events.
- Restored automatic reading of legacy WSR alternates and spelling panels and their visible correction choices.
- Added duplicate suppression for both native-first and fallback-first callback ordering, while continuing to exclude recent physical keyboard input.
- Clarified which original DictationBridge features are preserved, modernized, or intentionally excluded.
- Confirmed in live testing that offline Windows Speech Recognition text is echoed and its correction choices are read automatically.
- Documented premature online word-fragment announcements followed by the completed word or phrase as a known beta bug.
- Limited tagged GitHub releases to the installable `.nvda-addon`; the SHA-256 digest is recorded in the workflow summary instead of uploaded as a second asset.

## 0.2.0 — 2026-08-11

First public beta.

- Modernized the original DictationBridge text-observation concept for current NVDA.
- Added automatic 32-bit or 64-bit native master selection.
- Added matching observers and loaders for both application architectures.
- Removed Dragon, Word automation, legacy WSR macros, and screen-reader voice commands.
- Preserved short-delay partial-phrase echo.
- Added deletion and replacement announcements.
- Restored and modernized automatic WSR training-prompt reading.
- Validated Windows+H partial phrases and selected-text replacement in Notepad on Windows 10.

Original project: <https://github.com/dictationbridge/dictationBridge>
