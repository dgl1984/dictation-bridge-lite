# Validation record

## Confirmed runtime behavior

On 11 August 2026, DictationBridge Lite was tested with current NVDA on Windows 10:

- The add-on installed and NVDA restarted without instability.
- Windows+H online voice typing inserted text into Notepad.
- NVDA spoke partial phrases while dictation continued.
- Dictating over a keyboard selection announced the removed text and its replacement.
- A Windows command tooltip and the following dictated text were both heard, confirming that the tooltip no longer suppresses the next echo.
- The Windows Speech Recognition training wizard automatically announced each passage.
- The grave-accent reread command worked in the training wizard.

Windows interpreted punctuation and command phrases as literal dictated text during this test. This behavior occurs inside Windows recognition rather than DictationBridge Lite.

On 12 August 2026, initial live testing confirmed that the version 0.2.1 repair speaks text inserted into Notepad by legacy offline Windows Speech Recognition. One correction panel was also read after saying `correct` followed by the incorrect words. Later testing showed that this panel result was not repeatable. The confirmed tooltip behavior remained intact.

Version 0.2.1 could announce incomplete online word fragments while Windows updated the text and then repeat the completed word or phrase. Version 0.3.0 replaces that behavior with finalized phrase-level speech.

Later testing on 12 August 2026 confirmed the version 0.3.0 behavior:

- Online Windows+H dictation reliably announces the finalized phrase without provisional fragments, repeated completed phrases, or rotating hint chatter.
- The online announcement is noticeably delayed because it waits for Windows to finalize and commit the phrase.
- Legacy offline dictated text remains as responsive as is realistic for Windows recognition and NVDA event delivery.
- The first correction panel was readable in one session, while later panels or a panel in a subsequent session could remain silent. In the silent case, the log contained no DictationBridge Lite panel-show event, confirming that the add-on had no panel object to read.
- Passing WSR panel events through NVDA removed the repeated Tony's Enhancements keyboard tracebacks seen in an earlier diagnostic build.
- The Run-dialog commands `ms-settings:privacy-speech` and `control /name Microsoft.SpeechRecognition` opened the intended online and offline Windows settings on the tested Windows 10 system.

## Build and structural checks

- NVDA Python sources compile without syntax errors.
- Native C and C++ sources compile with warnings treated as errors for i686 and x86-64 Windows targets.
- All six native files link using LLVM-MinGW 20260616 with a static compiler runtime.
- Master DLLs export the five `DBL_` entry points used by the NVDA plugin.
- In-process DLLs export `Attach`, `InstallHooks`, and `RemoveHooks`.
- Executables and DLLs import only Windows system libraries plus the matching in-process DLL used by each loader.
- The add-on archive contains the manifest, plugin, documentation, WSR training app module, and all six native files at the required paths.
- Python regression tests cover tooltip-safe speech, online composition separation, finalized-phrase duplicate filtering, online hint suppression, the two confirmed settings commands, offline typed-character, MSAA value-change, UIA text-change, inactive-WSR and physical-key exclusion, bidirectional insertion/deletion callback deduplication, and best-effort WSR correction handling.

## Remaining beta matrix

- Windows 11 voice typing and Voice Access.
- NVDA 2025.1 and 2026.1 as separate confirmed configurations.
- Notepad, Microsoft Word, Outlook, Firefox, Chrome, and other commonly dictated editors.
- Mixed 32-bit and 64-bit target applications.
- Confirming the new Tools submenu in a Windows-built 0.3.0 package.
- Finding a dependable event source for legacy WSR correction panels that Windows displays or reuses without a show event.
- Evaluating whether online feedback can be made earlier without reintroducing provisional fragments or completed-phrase repetition.
