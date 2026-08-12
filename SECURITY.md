# Security

Report suspected security problems privately to **info@lanesaudio.com** before opening a public issue.

DictationBridge Lite does not make network connections and does not receive microphone audio. Its native observer uses Windows in-context event hooks and API interception to observe text insertion inside applications. This is powerful behavior and may attract antivirus scrutiny; releases therefore include source code, reproducible build automation, and SHA-256 checksums.

Windows voice typing itself may use Microsoft's online speech-recognition service. That network activity belongs to Windows and is controlled by Windows privacy settings.
