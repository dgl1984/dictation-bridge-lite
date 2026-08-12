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

On 12 August 2026, live testing confirmed that the version 0.2.1 repair speaks text inserted into Notepad by legacy offline Windows Speech Recognition. It also automatically reads the correction suggestions opened by saying `correct` followed by the incorrect words. The confirmed tooltip behavior remained intact. These are restored preserved features, not intentional removals.

During online Windows+H dictation, NVDA can announce incomplete word fragments while Windows is still updating the text and then announce the completed word or phrase. The final result is spoken correctly, but the premature fragment speech is a known beta bug.

## Build and structural checks

- NVDA Python sources compile without syntax errors.
- Native C and C++ sources compile with warnings treated as errors for i686 and x86-64 Windows targets.
- All six native files link using LLVM-MinGW 20260616 with a static compiler runtime.
- Master DLLs export the five `DBL_` entry points used by the NVDA plugin.
- In-process DLLs export `Attach`, `InstallHooks`, and `RemoveHooks`.
- Executables and DLLs import only Windows system libraries plus the matching in-process DLL used by each loader.
- The add-on archive contains the manifest, plugin, documentation, WSR training app module, and all six native files at the required paths.
- Fifteen Python regression tests cover the confirmed tooltip-safe speech path, offline typed-character, MSAA value-change, and UIA text-change paths, inactive-WSR and physical-key exclusion, bidirectional insertion/deletion callback deduplication, and WSR correction-panel discovery and automatic speech.

## Remaining beta matrix

- Windows 11 voice typing and Voice Access.
- NVDA 2025.1 and 2026.1 as separate confirmed configurations.
- Notepad, Microsoft Word, Outlook, Firefox, Chrome, and other commonly dictated editors.
- Mixed 32-bit and 64-bit target applications.
- Reducing premature word-fragment announcements during online Windows+H dictation without delaying useful phrase feedback.
