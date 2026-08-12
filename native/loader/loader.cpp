/* Copyright (C) 2016-2020 Three Mouse Technology, LLC and DictationBridge contributors
 * Copyright (C) 2026 Derek Lane and DictationBridge Lite contributors
 * SPDX-License-Identifier: MPL-2.0
 */

#include <windows.h>

#include "protocol.h"

extern "C" BOOL WINAPI InstallHooks();
extern "C" void WINAPI RemoveHooks();

namespace {

bool masterRunning() {
	return FindWindowExW(HWND_MESSAGE, nullptr, dbl::kMasterWindowClass, nullptr) != nullptr;
}

void pumpFor(DWORD milliseconds) {
	const ULONGLONG finish = GetTickCount64() + milliseconds;
	MSG message{};
	while (GetTickCount64() < finish) {
		const DWORD remaining = static_cast<DWORD>(finish - GetTickCount64());
		MsgWaitForMultipleObjects(0, nullptr, FALSE, remaining, QS_ALLINPUT | QS_ALLEVENTS);
		while (PeekMessageW(&message, nullptr, 0, 0, PM_REMOVE)) {
			TranslateMessage(&message);
			DispatchMessageW(&message);
		}
	}
}

} // namespace

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
	if (!InstallHooks()) {
		return 1;
	}
	while (masterRunning()) {
		pumpFor(250);
	}
	RemoveHooks();
	return 0;
}
