# DictationBridge Lite 0.3.0 beta

DictationBridge Lite makes NVDA speak text entered through Windows dictation. It supports two different Windows 10 recognition systems: online voice typing and legacy offline Windows Speech Recognition. The add-on does not perform speech recognition itself. It observes text after Windows inserts or replaces it.

This is an independent modernization of the [original DictationBridge project](https://github.com/dictationbridge/dictationBridge). It is not an official release by, or an endorsement from, the original maintainers. Dragon support, legacy speech macros, and screen-reader voice commands are intentionally excluded.

## Choose a dictation system

Online and offline dictation are useful for different reasons.

### Online dictation

- Start it in an editable field with Windows+H. See Microsoft's [voice typing instructions](https://support.microsoft.com/en-us/accessibility/windows/use-voice-typing-to-talk-instead-of-type-on-your-pc).
- It generally provides better recognition without voice training.
- It uses Microsoft's online speech-recognition service on Windows 10.
- Windows may ask you to pause while it catches up.
- DictationBridge Lite waits for Windows to finalize a phrase, then allows NVDA to announce that phrase once. This avoids the incomplete word fragments and repeated completed phrases heard in earlier versions, but it creates a noticeable delay.
- Windows rotating tips and routine “Listening” or “Thinking” messages are suppressed. Genuine error messages remain available.
- Correction facilities are more limited than legacy offline Speech Recognition.

### Offline Windows Speech Recognition

- It can dictate continuously with responsive NVDA feedback and does not require Microsoft's online recognition service.
- Initial accuracy may be lower, but Windows provides microphone setup and voice-training tools that can improve it.
- It supports spoken correction commands and a correction choices panel.
- Dictated text itself is announced reliably in current Windows 10 testing.
- Correction-panel speech is not dependable with NVDA 2026.1. Windows can display or reuse a correction panel without delivering an event that the add-on can read. Some panels or Windows feedback may be announced while another correction panel remains silent.

## Open the Windows settings

Open the NVDA menu, choose **Tools**, then **DictationBridge Lite**.

- **Online dictation settings...** opens Windows Privacy > Speech, where online speech recognition can be enabled or disabled.
- **Offline Speech Recognition settings...** opens the legacy Speech Recognition Control Panel for microphone setup, training, tutorials, and recognition controls.
- **Speak dictated text** turns DictationBridge Lite announcements on or off. It does not start or stop either Windows recognizer.

These menu items use the same Windows commands confirmed during Windows 10 testing:

- Online settings: `ms-settings:privacy-speech`
- Offline Speech Recognition Control Panel: `control /name Microsoft.SpeechRecognition`

If necessary, either command can also be entered manually in the Windows Run dialog.

## Start online dictation

1. Make sure online speech recognition is enabled in Windows settings.
2. Put the caret in an editable text field.
3. Press Windows+H.
4. Dictate a phrase, then pause long enough for Windows to finalize it.

DictationBridge Lite separates Windows' temporary composition text from text committed to the document. Temporary fragments and spoken command words are not announced. NVDA announces the completed phrase after Windows commits it, and an exact rapid duplicate is suppressed.

## Set up and use offline Speech Recognition

1. Open **NVDA menu > Tools > DictationBridge Lite > Offline Speech Recognition settings...**.
2. Use **Set up microphone** before the first dictation session.
3. Use **Train your computer to better understand you** if recognition accuracy needs improvement.
4. Start Windows Speech Recognition from its Control Panel or another Windows-provided entry point.
5. Put the caret in an editable field and begin dictating.

Microsoft's [Windows Speech Recognition instructions](https://support.microsoft.com/en-us/windows/use-voice-recognition-in-windows-83ff75bd-63eb-0b6c-18d4-6fae94050571) document Windows+Ctrl+S for opening Speech Recognition after setup, but live testing found that shortcut unreliable on one Windows 10 system: it could stop recognition while failing to start it again. The Speech Recognition Control Panel remains the dependable route to setup and other controls.

## Windows Speech Recognition training

The Windows 10 Speech Recognition training wizard is supported. DictationBridge Lite automatically reads each new training passage and places it under the NVDA review cursor. Press the grave-accent key, usually immediately to the left of `1`, to read the current passage again while the training wizard is active.

## Dictated-text feedback

Offline insertions are combined for 100 milliseconds before they are spoken. This keeps feedback responsive while avoiding character-by-character speech. New lines, new paragraphs, deleted text, and replacement text are also reported.

Online composition is handled differently. Temporary recognition changes are ignored, and the finalized phrase is left for NVDA to announce when Windows returns focus to the editor. This trades immediate fragments for cleaner phrase-level feedback.

The add-on still has an assignable **Toggle DictationBridge Lite text echo** command. In NVDA's Input Gestures dialog, look under **DictationBridge Lite** to give it a shortcut.

## Privacy and responsibility boundaries

DictationBridge Lite does not receive microphone audio and does not make network connections. Online Windows+H dictation sends speech to Microsoft's service according to Windows privacy settings. Offline Windows Speech Recognition processes recognition locally.

Recognition accuracy, punctuation, spoken commands, training data, and Windows' “hold on while we catch up” behavior belong to Windows. DictationBridge Lite reports the resulting text and selected Windows feedback through NVDA.

## Native and compatibility modes

The complete build includes 32-bit and 64-bit native observers. It automatically uses the master library matching the running NVDA architecture and can observe both 32-bit and 64-bit applications.

If the native files are absent or fail to start, the add-on enters Python-only compatibility mode. That mode works only in controls where NVDA exposes enough text events and does not provide dependable replacement reporting.

## Supported and tested systems

- Live-tested: Windows 10 22H2 with NVDA 2026.1.1 AMD64 and Notepad.
- Supported NVDA API range: NVDA 2025.1 through 2026.1.
- Windows 11 and applications beyond Notepad remain part of the wider beta test matrix.
- On Windows 11 22H2 and later, Microsoft replaced legacy Windows Speech Recognition with Voice Access. DictationBridge Lite's legacy offline support is primarily intended for Windows 10.

## Troubleshooting

Start with Notepad. Confirm that normal keyboard typing is left alone and that dictated text appears before testing another application.

If no dictated text is spoken, restart NVDA with logging set to debug and look for lines beginning with `DictationBridge Lite`. Confirm that the installed add-on contains both loader programs, both master DLLs, and both in-process DLLs.

For online dictation, confirm that online speech recognition is enabled and allow Windows time to finalize the phrase. For offline dictation, confirm that Windows Speech Recognition is running and that microphone setup has been completed.

If an offline correction panel is visible but silent, this is a known compatibility limitation. A useful report includes the Windows and NVDA versions, whether the first or a later correction failed, and relevant `DictationBridge Lite` or traceback lines from the NVDA log.

## Licensing and credit

This is an independent modernization of DictationBridge, originally developed by Three Mouse Technology, LLC and project contributors. Native bridge code is provided under MPL 2.0, NVDA integration under GPL 2.0, and MinHook under its BSD-style license. License texts and third-party notices are included in the add-on package; corresponding source is available from the project homepage.
