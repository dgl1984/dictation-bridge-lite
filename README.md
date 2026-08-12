# DictationBridge Lite

DictationBridge Lite is an NVDA add-on that speaks text and replacements entered through Windows dictation, including online voice typing (`Windows+H`) and legacy offline Windows Speech Recognition. Its short echo interval lets users hear results while they are still dictating and correct text as they work.

**Current release: 0.2.1 beta.** Download the versioned `.nvda-addon` from [GitHub Releases](https://github.com/dgl1984/dictation-bridge-lite/releases). The installable add-on is the only file intentionally attached to each release; GitHub provides the matching source archives automatically.

This is an independent modernization of the [original DictationBridge project](https://github.com/dictationbridge/dictationBridge). It is not an official release by, or an endorsement from, the original maintainers.

## What DictationBridge Lite does

- Echoes Windows voice-typing text through NVDA after a short 100 millisecond pause.
- Speaks partial phrases while dictation continues.
- Announces text removed and replaced by further dictation.
- Reports inserted new lines and new paragraphs.
- Keeps the next dictated-text announcement audible when Windows displays a transient command or suggestion tooltip.
- Makes the Windows Speech Recognition training wizard accessible, including automatic passage announcements and a command to reread the current passage.
- Observes text only after Windows inserts it; it does not receive microphone audio or make network connections.

## Added or modernized in DictationBridge Lite

- Support for current NVDA APIs, including 32-bit NVDA 2025 and the 64-bit NVDA 2026 API series.
- Automatic selection of the native master library that matches NVDA's process architecture.
- Matching 32-bit and 64-bit observers and loaders so both application architectures can be observed.
- Fixed-width cross-architecture IPC fields and safer native-hook startup and shutdown.
- Generic Text Services Framework observation instead of application-specific Word automation.
- Deletion and replacement announcements when dictation overwrites selected text.
- In version 0.2.1, delayed immediate-priority announcements so command and suggestion tooltips do not suppress the next dictated phrase.
- Added a focused-editable-text snapshot fallback for legacy offline Windows Speech Recognition when current NVDA receives a value change but no TSF or typed-character event.
- Restored automatic reading of the legacy WSR alternates and spelling panels, including their visible correction choices.
- A current CMake and Visual Studio 2022 build, automated GitHub validation, and a reproducible tagged-release workflow.

## Features preserved from the original DictationBridge

- The central accessibility feature: the screen reader echoes dictated text as it is inserted.
- Short-delay feedback that allows users to hear and correct dictation while continuing to speak.
- Spoken feedback for new lines and new paragraphs.
- Accessibility support for Windows Speech Recognition training passages.
- Legacy offline Windows Speech Recognition dictated-text echo, restored for current NVDA in version 0.2.1 and confirmed in live testing.
- Automatic speech for legacy Windows Speech Recognition correction choices.
- Background operation as an NVDA add-on rather than a separate user-facing application.
- The original project's open-source licensing, attribution, and MinHook-based native observation lineage.

## How the original functions map to DictationBridge Lite

DictationBridge Lite intentionally has a smaller scope than the original DictationBridge. The table below explains how each major function originally worked and what Lite uses now. “Removed” means there is no replacement in Lite; it does not mean that the feature is merely broken.

| Function | How the original DictationBridge worked | How DictationBridge Lite works now |
| --- | --- | --- |
| Dictated-text capture | A native core injected hooks into target applications. It observed Text Services Framework operations and also carried product-specific hooks for Dragon and Microsoft Word. A synthetic NVDA typed-character path helped with legacy WSR. | Matching 32-bit and 64-bit native observers watch generic Text Services Framework insertions. Lite keeps the typed-character path and adds a focused editable-text snapshot fallback while legacy WSR is running. Reports from overlapping paths are deduplicated. **Status: preserved and modernized.** |
| Echo timing and tooltip handling | Adjacent insertions were combined for 100 milliseconds and then sent directly to screen-reader speech. New lines, paragraphs, and braille caret refreshes were also reported. A transient tooltip could cancel the next direct speech request on current NVDA. | Lite retains the 100 millisecond combining interval, line and paragraph feedback, and braille refresh. It delivers each completed announcement on NVDA's next core cycle at immediate priority, allowing both a tooltip and the following dictated text to be heard. **Status: preserved and repaired.** |
| Deleted and replacement text | Native deletion and insertion callbacks reported text removed or replaced by dictation. | Lite reports deletion and insertion through the modern native path and the offline fallback, with two-way deduplication when a control exposes the same edit through more than one event route. **Status: preserved and modernized.** |
| Legacy offline WSR echo | The original typed-character handler treated characters arriving without a recent physical keypress as dictated input and passed them into the same short-delay echo buffer. | Current NVDA and Notepad can expose offline WSR insertion only as a focused edit value or text change. Lite snapshots that edit while WSR is running, calculates the inserted or deleted portion, excludes recent physical typing, and sends the result through the same echo buffer. **Status: preserved and repaired in 0.2.1.** |
| WSR correction and spelling panels | The original requested show events for WSR dialog windows, applied NVDA overlay classes, read visible instructions and alternatives, added panel navigation scripts, and polled the spelling word for changes. | Lite restores current-NVDA detection of the alternates and spelling panels and automatically reads their visible prompt and choices through the tooltip-safe speech route. Standard WSR and NVDA controls handle navigation and activation; the original custom panel key scripts are not included. **Status: core speech preserved; custom key layer removed.** |
| WSR training wizard | An NVDA application module detected each training passage, announced it, placed it under the review cursor, and provided the grave-accent reread command. | Lite retains that workflow in a current-NVDA application module, including automatic passage speech, review-cursor placement, and the reread command. **Status: preserved and modernized.** |
| Microsoft Word support | The original native layer included Word-specific hooks and automation in addition to its general text observation. | Lite does not automate Word. Its generic Text Services Framework observer can work in compatible editors without carrying a separate Word integration layer. **Status: specialized implementation removed and replaced by generic observation.** |
| Dragon integration and microphone status | Dragon-specific native hooks and NVDA application modules exposed dictated text, vocabulary controls, and microphone on, off, or sleeping status. The add-on could also build and install Dragon command data. | Lite does not load Dragon hooks, inspect Dragon UI, report Dragon microphone status, or install Dragon commands. It focuses on Windows dictation. **Status: removed with no replacement.** |
| Screen-reader and WSR command macros | The original repository generated and packaged voice-command data for NVDA, JAWS, Dragon, and Microsoft Speech Recognition, alongside a screen-reader-independent core. | Lite passively reports text and WSR correction choices. It neither installs voice-command macros nor controls NVDA or JAWS by voice, and it is packaged only as an NVDA add-on. **Status: removed with no replacement.** |
| Build and process architecture | The original used Python 2, SCons, Visual Studio 2015-era projects, and its older cross-process protocol. | Lite uses current NVDA Python, CMake, Visual Studio 2022, fixed-width IPC fields, architecture-matched native masters, and 32-bit and 64-bit loaders and observers. GitHub Actions builds and packages tagged releases. **Status: replaced.** |

The deliberately removed capabilities keep the add-on maintainable and focused on dictated-text feedback. Offline WSR echo and correction-panel speech are preserved features, not exclusions. DictationBridge Lite does not control Windows recognition accuracy, punctuation handling, or the spoken commands understood by Windows itself.

## Public beta status

On Windows 10 with current NVDA, testing has confirmed:

- clean installation and NVDA startup;
- partial-phrase echo from Windows+H voice typing in Notepad;
- announcement of selected text removed and replaced by further dictation;
- simultaneous speech of a Windows command tooltip and the following dictated text, confirming the tooltip-race repair;
- legacy offline Windows Speech Recognition dictated-text echo;
- automatic reading of legacy WSR correction choices; and
- automatic reading of Windows Speech Recognition training passages.

Version 0.2.1 has regression coverage for tooltip-resistant dictated text, line breaks, deletions, physical-key exclusion, callback deduplication, offline editable-value changes, and automatic WSR correction-panel reading. Live testing confirmed the two offline repairs and confirmed that the tooltip fix remains effective.

**Known beta bug:** during online Windows+H dictation, NVDA can announce incomplete word fragments as Windows updates the text and then announce the completed word or phrase. The final result is still spoken, but the preliminary fragments can be noisy. This is being published as a known bug rather than treated as an intentional feature. Windows 11 and a broader range of applications also remain part of the community test matrix.

## Privacy and responsibility boundaries

On Windows 10, Windows+H voice typing requires Microsoft's online speech-recognition service. DictationBridge Lite does not make network connections and does not receive microphone audio. It observes text only after Windows inserts or replaces it in an application.

Recognition accuracy, punctuation, and interpretation of spoken commands belong to Windows. DictationBridge Lite only reports resulting text operations through NVDA.

## Install and test

Install the `.nvda-addon` file, restart NVDA, and test both online Windows+H dictation and legacy offline Windows Speech Recognition in Notepad. Dictate several sentences and replace selected text with further dictation. In offline mode, say `correct` followed by incorrect words and confirm that the correction choices are read automatically. Also trigger a command suggestion such as `select all` and continue dictating while its tooltip is visible; both the tooltip and dictated text should remain audible.

Useful test results include:

1. Windows and NVDA versions.
2. Application name and architecture when known.
3. Whether partial phrases were spoken.
4. Whether ordinary keyboard input was left alone.
5. Whether removed and replacement text were announced.
6. Whether the next dictated phrase was heard while a command or suggestion tooltip was visible.
7. Whether offline WSR text was echoed after it appeared in Notepad.
8. Whether the offline WSR correction choices were read automatically.
9. Relevant lines beginning with `DictationBridge Lite` from the NVDA log.

## Build on Windows

Install Visual Studio 2022 with **Desktop development with C++** and its CMake tools. Run:

```text
build.cmd
```

The finished add-on is placed in the `output` directory. To package the limited Python-only compatibility probe without compiling native components, run `build.cmd probe`.

The tagged-release workflow publishes only the `.nvda-addon` as a GitHub release asset. It records the SHA-256 digest in the workflow summary for verification without attaching a second checksum file.

## Licensing and credit

Copyright for the original work remains with Three Mouse Technology, LLC and the original DictationBridge contributors. New work is copyright 2026 Derek Lane and DictationBridge Lite contributors.

The project contains code under MPL 2.0, GPL 2.0, and the BSD license used by MinHook. See [LICENSES.md](LICENSES.md) for the exact mapping and required notices.
