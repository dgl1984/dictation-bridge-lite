# DictationBridge Lite 0.2.1 beta

DictationBridge Lite makes NVDA speak text entered through Windows voice typing. It is a focused continuation of DictationBridge's useful text-echo feature. Dragon support, legacy speech macros, and screen-reader voice commands are intentionally excluded. Legacy Windows Speech Recognition dictated-text and correction-panel feedback remain intended features.

DictationBridge Lite is an independent modernization of the [original DictationBridge project](https://github.com/dictationbridge/dictationBridge). It is not an official release by, or an endorsement from, the original maintainers.

## Using it

1. Install the add-on and restart NVDA.
2. Put the caret in an editable text field.
3. Press Windows+H and begin dictating.

Dictated text is spoken after a short 100 millisecond pause. This deliberately allows partial phrases to be heard while you are still speaking. When Windows replaces or deletes text during a correction, DictationBridge Lite also reports the removed text and then speaks the replacement.

Dictated text remains prioritized when Windows displays transient command or suggestion tooltips. Live testing confirmed that NVDA can speak both the tooltip and the following dictated text.

Legacy offline Windows Speech Recognition is also monitored. When its correction alternates or spelling panel appears, DictationBridge Lite automatically reads the visible prompt and choices.

**Known beta bug:** during online Windows+H dictation, NVDA can announce incomplete word fragments while Windows is updating the text and then announce the completed word or phrase. The final result is still spoken, but the preliminary fragments can be noisy.

The add-on has no assigned global shortcut. In NVDA's Input Gestures dialog, look under **DictationBridge Lite** if you want to assign a gesture to **Toggle DictationBridge Lite text echo**.

## Windows Speech Recognition training

The Windows 10 Speech Recognition training wizard is supported. DictationBridge Lite automatically reads each new training passage and places it under the NVDA review cursor. Press the grave-accent key (usually immediately to the left of `1`) to read the current passage again while the training wizard is active.

## Native and compatibility modes

The complete build includes 32-bit and 64-bit native observers. It automatically uses the correct master library for the running NVDA version and observes both 32-bit and 64-bit applications.

If the native files are absent or fail to start, the add-on enters Python-only compatibility mode. This mode can echo voice typing only in applications where NVDA produces synthetic typed-character events. It is intended for initial testing and does not provide dependable correction reporting.

## Supported targets

- Windows 10 22H2 and Windows 11
- NVDA 2025.1 through the NVDA 2026 API series
- Windows voice typing opened with Windows+H

On Windows 10, Windows+H voice typing requires Microsoft's online speech-recognition service. DictationBridge Lite does not make network connections itself and does not receive microphone audio; it observes text after Windows inserts it. Punctuation, recognition accuracy, and spoken Windows commands are controlled by Windows rather than this add-on.

## Troubleshooting

If no dictated text is spoken, restart NVDA with logging set to debug and look for lines beginning with `DictationBridge Lite`. Confirm that both loader programs and both in-process DLLs are present in the installed add-on directory.

For an initial test, use Notepad. Browser and office-document support should be tested after Notepad works because their editable controls use several different accessibility and text-input implementations.

Please note whether partial phrases are spoken, normal keyboard typing is left alone, deletions are announced, replacement text is spoken, and legacy WSR correction choices are read automatically. Those observations are the most useful results from an initial test.

The legacy offline Windows Speech Recognition training wizard is made accessible. Version 0.2.1 adds a focused editable-value-change fallback and restores alternates/spelling-panel speech. Live testing confirmed that offline dictated text and correction suggestions are now spoken. These are repairs to intended features, not intentional exclusions.

## Licensing and credit

This is an independent modernization of DictationBridge, originally developed by Three Mouse Technology, LLC and project contributors. Native bridge code is provided under MPL 2.0, NVDA integration under GPL 2.0, and MinHook under its BSD-style license. License texts and third-party notices are included in the add-on package; corresponding source is available from the project homepage.
