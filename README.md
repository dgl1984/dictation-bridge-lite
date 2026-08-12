# DictationBridge Lite

DictationBridge Lite is an NVDA add-on that speaks text and replacements entered through Windows dictation, including online voice typing (`Windows+H`) and legacy offline Windows Speech Recognition. Offline text uses a short echo interval; online text is announced after Windows finalizes a phrase.

**Next release: 0.3.0 beta.** After the candidate has passed Windows testing, download the versioned `.nvda-addon` from [GitHub Releases](https://github.com/dgl1984/dictation-bridge-lite/releases). The installable add-on is the only file intentionally attached to each release; GitHub provides the matching source archives automatically.

This is an independent modernization of the [original DictationBridge project](https://github.com/dictationbridge/dictationBridge). It is not an official release by, or an endorsement from, the original maintainers.

## What DictationBridge Lite does

- Echoes legacy offline Windows Speech Recognition text through NVDA after a short 100 millisecond pause.
- Separates temporary Windows+H composition from committed text so online dictation is announced as a finalized phrase rather than incomplete fragments.
- Suppresses an exact rapid repeat of the finalized online phrase.
- Suppresses rotating online tips and routine Listening or Thinking messages while preserving genuine errors.
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
- Restored best-effort reading of legacy WSR alternates and spelling panels when Windows exposes a usable panel event.
- A current CMake and Visual Studio 2022 build, automated GitHub validation, and a reproducible tagged-release workflow.
- A discoverable **NVDA menu > Tools > DictationBridge Lite** submenu for online settings, offline Speech Recognition settings, and the echo toggle.

## Choose and configure a recognition system

DictationBridge Lite supports two different Windows 10 dictation paths. Neither is universally better.

- **Online Windows+H dictation** generally provides better recognition without voice training. It requires Microsoft's online speech-recognition service, may tell the user to wait while Windows catches up, and offers fewer correction facilities. Version 0.3.0 waits for Windows to finalize a phrase before NVDA announces it, trading immediate fragments for clean phrase-level feedback.
- **Legacy offline Windows Speech Recognition** can dictate continuously with responsive feedback and works without Microsoft's online recognition service. Initial accuracy may be lower, but Windows provides microphone setup and voice training. Its correction panel remains unreliable with NVDA 2026.1 even though ordinary offline dictated text is announced reliably.

The add-on's Tools submenu opens the two Windows locations that were confirmed on Windows 10:

- **Online dictation settings...** uses `ms-settings:privacy-speech`.
- **Offline Speech Recognition settings...** uses `control /name Microsoft.SpeechRecognition`.
- **Speak dictated text** enables or disables DictationBridge Lite feedback; it does not start or stop Windows recognition.

To use online dictation, focus an editable field and press Windows+H; Microsoft provides [voice typing instructions](https://support.microsoft.com/en-us/accessibility/windows/use-voice-typing-to-talk-instead-of-type-on-your-pc). Microsoft's [Windows Speech Recognition instructions](https://support.microsoft.com/en-us/windows/use-voice-recognition-in-windows-83ff75bd-63eb-0b6c-18d4-6fae94050571) document Windows+Ctrl+S after setup, but live testing found that shortcut could stop recognition and then fail to restart it. The Speech Recognition Control Panel is the dependable route to setup, training, and other controls on that system.

## Features preserved from the original DictationBridge

- The central accessibility feature: the screen reader echoes dictated text as it is inserted.
- Short-delay feedback that allows users to hear and correct dictation while continuing to speak.
- Spoken feedback for new lines and new paragraphs.
- Accessibility support for Windows Speech Recognition training passages.
- Legacy offline Windows Speech Recognition dictated-text echo, restored for current NVDA in version 0.2.1 and confirmed in live testing.
- Best-effort speech for legacy Windows Speech Recognition correction choices when Windows exposes the panel to NVDA.
- Background operation as an NVDA add-on rather than a separate user-facing application.
- The original project's open-source licensing, attribution, and MinHook-based native observation lineage.

## How the original functions map to DictationBridge Lite

DictationBridge Lite intentionally has a smaller scope than the original DictationBridge. The table below explains how each major function originally worked and what Lite uses now. “Removed” means there is no replacement in Lite; it does not mean that the feature is merely broken.

| Function | How the original DictationBridge worked | How DictationBridge Lite works now |
| --- | --- | --- |
| Dictated-text capture | A native core injected hooks into target applications. It observed Text Services Framework operations and also carried product-specific hooks for Dragon and Microsoft Word. A synthetic NVDA typed-character path helped with legacy WSR. | Matching 32-bit and 64-bit native observers watch generic Text Services Framework insertions. Lite keeps the typed-character path and adds a focused editable-text snapshot fallback while legacy WSR is running. Reports from overlapping paths are deduplicated. **Status: preserved and modernized.** |
| Echo timing and online composition | Adjacent insertions were combined for 100 milliseconds and then sent directly to screen-reader speech. New lines, paragraphs, and braille caret refreshes were also reported. | Lite retains the 100 millisecond path for offline dictation. For online Windows+H input, it distinguishes Windows' temporary Composition object from the real editor, ignores provisional fragments and commit churn, and suppresses an exact rapid duplicate of the finalized phrase. **Status: preserved and adapted to current Windows behavior.** |
| Deleted and replacement text | Native deletion and insertion callbacks reported text removed or replaced by dictation. | Lite reports deletion and insertion through the modern native path and the offline fallback, with two-way deduplication when a control exposes the same edit through more than one event route. **Status: preserved and modernized.** |
| Legacy offline WSR echo | The original typed-character handler treated characters arriving without a recent physical keypress as dictated input and passed them into the same short-delay echo buffer. | Current NVDA and Notepad can expose offline WSR insertion only as a focused edit value or text change. Lite snapshots that edit while WSR is running, calculates the inserted or deleted portion, excludes recent physical typing, and sends the result through the same echo buffer. **Status: preserved and repaired in 0.2.1.** |
| WSR correction and spelling panels | The original requested show events for WSR dialog windows, applied NVDA overlay classes, read visible instructions and alternatives, added panel navigation scripts, and polled the spelling word for changes. | Lite requests current-NVDA panel events, delays reading until choices are populated, and reports actionable WSR feedback. Windows can nevertheless display or reuse a panel without delivering a usable event on NVDA 2026.1, so automatic panel speech is best effort. Standard WSR and NVDA controls handle navigation; the original custom key layer is not included. **Status: partially preserved with a documented compatibility limitation.** |
| WSR training wizard | An NVDA application module detected each training passage, announced it, placed it under the review cursor, and provided the grave-accent reread command. | Lite retains that workflow in a current-NVDA application module, including automatic passage speech, review-cursor placement, and the reread command. **Status: preserved and modernized.** |
| Microsoft Word support | The original native layer included Word-specific hooks and automation in addition to its general text observation. | Lite does not automate Word. Its generic Text Services Framework observer can work in compatible editors without carrying a separate Word integration layer. **Status: specialized implementation removed and replaced by generic observation.** |
| Dragon integration and microphone status | Dragon-specific native hooks and NVDA application modules exposed dictated text, vocabulary controls, and microphone on, off, or sleeping status. The add-on could also build and install Dragon command data. | Lite does not load Dragon hooks, inspect Dragon UI, report Dragon microphone status, or install Dragon commands. It focuses on Windows dictation. **Status: removed with no replacement.** |
| Screen-reader and WSR command macros | The original repository generated and packaged voice-command data for NVDA, JAWS, Dragon, and Microsoft Speech Recognition, alongside a screen-reader-independent core. | Lite passively reports text and best-effort WSR correction feedback. It neither installs voice-command macros nor controls NVDA or JAWS by voice, and it is packaged only as an NVDA add-on. **Status: removed with no replacement.** |
| Build and process architecture | The original used Python 2, SCons, Visual Studio 2015-era projects, and its older cross-process protocol. | Lite uses current NVDA Python, CMake, Visual Studio 2022, fixed-width IPC fields, architecture-matched native masters, and 32-bit and 64-bit loaders and observers. GitHub Actions builds and packages tagged releases. **Status: replaced.** |

The deliberately removed capabilities keep the add-on maintainable and focused on dictated-text feedback. Offline WSR echo remains a preserved feature; correction-panel speech is best effort because the required Windows event is not always delivered. DictationBridge Lite does not control Windows recognition accuracy, punctuation handling, or the spoken commands understood by Windows itself.

## Public beta status

On Windows 10 with current NVDA, testing has confirmed:

- clean installation and NVDA startup;
- finalized phrase-level speech from Windows+H voice typing without provisional fragments or repeated completed phrases;
- suppression of rotating online dictation hints and routine status chatter;
- announcement of selected text removed and replaced by further dictation;
- simultaneous speech of a Windows command tooltip and the following dictated text, confirming the tooltip-race repair;
- responsive legacy offline Windows Speech Recognition dictated-text echo;
- automatic reading of Windows Speech Recognition training passages.

Version 0.3.0 adds regression coverage for online composition separation, finalized-phrase duplicate suppression, online hint suppression, settings-menu command targets, offline echo, callback deduplication, and best-effort WSR panel handling. Live Windows 10 testing confirmed that ordinary offline feedback is responsive and that online finalized phrases are announced reliably.

**Known beta limitations:** online phrase feedback is delayed until Windows finalizes the phrase. Legacy offline correction panels are not announced consistently because Windows can display or reuse them without delivering a usable NVDA event. Windows 11 and a broader range of applications remain part of the community test matrix.

## Privacy and responsibility boundaries

On Windows 10, Windows+H voice typing requires Microsoft's online speech-recognition service. DictationBridge Lite does not make network connections and does not receive microphone audio. It observes text only after Windows inserts or replaces it in an application.

Recognition accuracy, punctuation, and interpretation of spoken commands belong to Windows. DictationBridge Lite only reports resulting text operations through NVDA.

## Install and test

Install the `.nvda-addon` file, restart NVDA, and find **DictationBridge Lite** under NVDA's **Tools** menu. Confirm that the online and offline settings items open the intended Windows pages. Test both online Windows+H dictation and legacy offline Windows Speech Recognition in Notepad. Dictate several sentences and replace selected text with further dictation. In offline mode, try more than one correction and report whether each panel is announced.

Useful test results include:

1. Windows and NVDA versions.
2. Application name and architecture when known.
3. Whether online dictation announced one finalized phrase without preliminary fragments or a repeated final phrase.
4. Whether ordinary keyboard input was left alone.
5. Whether removed and replacement text were announced.
6. Whether rotating online hints and routine status chatter remained silent while genuine errors were preserved.
7. Whether offline WSR text was echoed after it appeared in Notepad.
8. Whether the first and later offline WSR correction panels were read automatically.
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
