@rem Copyright (C) 2026 Derek Lane and DictationBridge Lite contributors
@rem SPDX-License-Identifier: GPL-2.0-only
@echo off
setlocal
cd /d "%~dp0"
if /i "%~1"=="probe" (
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" -SkipNative
) else (
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1"
)
if errorlevel 1 (
	echo.
	echo Build failed. Review the error above.
	pause
	exit /b 1
)
echo.
echo The add-on is in the output folder.
pause
