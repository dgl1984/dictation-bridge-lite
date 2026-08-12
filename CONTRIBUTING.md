# Contributing

Bug reports and application-compatibility results are welcome. Please include:

- Windows version;
- NVDA version;
- target application and version;
- whether the application is 32-bit or 64-bit, if known;
- exact steps and resulting text;
- what NVDA spoke; and
- relevant NVDA log lines beginning with `DictationBridge Lite`.

Do not include dictated private information, microphone recordings, passwords, or unrelated NVDA log contents.

Native changes should build for both Win32 and x64 with warnings treated as errors. Python changes should remain compatible with the minimum NVDA version declared in `addon/manifest.ini`.
