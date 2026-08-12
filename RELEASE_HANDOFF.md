# DictationBridge Lite 0.3.0 release handoff

This tree is prepared for a 0.3.0 public-beta update. It should be reviewed, built by the existing Windows GitHub Actions workflow, smoke-tested by Derek with NVDA, and only then tagged for release.

## Intended release scope

- Clean online Windows+H feedback: ignore provisional Composition text, announce the finalized phrase once, and suppress rotating hints and routine status chatter.
- Preserve responsive legacy offline Windows Speech Recognition dictated-text feedback.
- Treat offline correction-panel speech as best effort. Do not describe it as fixed or guaranteed; Windows sometimes displays or reuses the panel without delivering a usable NVDA event.
- Add **NVDA menu > Tools > DictationBridge Lite** with:
  - **Online dictation settings...**, launching `ms-settings:privacy-speech`.
  - **Offline Speech Recognition settings...**, launching `control /name Microsoft.SpeechRecognition`.
  - **Speak dictated text**, synchronized with the existing echo toggle.
- Replace the 0.2.1 fragment-warning documentation with the observed 0.3.0 tradeoff: clean online phrases arrive only after Windows finalizes them.

The two Windows settings commands were entered manually in the Run dialog and confirmed on Derek's Windows 10 22H2 system before they were added to the menu.

## Required review and validation

1. Review the complete diff against `main`, especially the global plugin, menu cleanup on add-on reload, documentation claims, and version metadata.
2. Run the Python syntax check and all unit tests.
3. Push the prepared source to a review branch or `main` according to the repository's normal workflow.
4. Let **Build add-on** compile fresh Win32 and x64 native files and create the versioned package. Do not upload a locally repacked diagnostic build as the public release.
5. Give Derek the workflow artifact for this Windows/NVDA smoke test:
   - The DictationBridge Lite submenu appears under NVDA's Tools menu.
   - Online settings opens Privacy > Speech.
   - Offline settings opens the legacy Speech Recognition Control Panel.
   - Speak dictated text toggles and remains synchronized with the assignable command.
   - Online Windows+H produces one finalized phrase without fragments, a repeated final phrase, rotating tips, or routine Listening/Thinking chatter.
   - Offline dictated text remains responsive.
   - NVDA reloads or exits without a stale or duplicated Tools submenu.
6. Keep a correction-panel test in the smoke test, but treat a silent panel as the documented remaining limitation rather than a release blocker unless the add-on causes a new NVDA error.
7. After Derek approves the workflow artifact, tag it `v0.3.0-beta.1`. The existing release workflow should publish exactly one asset: `DictationBridgeLite-0.3.0.nvda-addon`.
8. Verify the release workflow's SHA-256 value and submit the release asset to VirusTotal before wider distribution.

## Suggested release notes

DictationBridge Lite 0.3.0 makes online and offline Windows dictation easier to find and substantially cleans up Windows+H feedback. Online dictation now announces the finalized phrase once instead of speaking provisional word fragments, repeated completed phrases, rotating tips, and routine status messages. Because it waits for Windows to finalize the phrase, its feedback is cleaner but delayed.

Legacy offline Windows Speech Recognition remains responsive and can be improved with Windows microphone setup and voice training. Correction-panel announcements are still best effort with NVDA 2026.1 because Windows does not always expose a usable panel event.

The new **NVDA menu > Tools > DictationBridge Lite** submenu opens the tested online and offline Windows settings and provides a checked dictated-text speech toggle.

## Distribution boundaries

- Continue describing the project as an independent modernization of the original DictationBridge.
- Do not claim that DictationBridge Lite performs recognition, receives microphone audio, controls recognition accuracy, or starts and stops Windows recognition.
- Do not claim dependable offline correction-panel speech.
- Keep the release in the beta channel while Windows 11 and the broader application matrix remain unconfirmed.
