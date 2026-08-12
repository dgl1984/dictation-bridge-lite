/* Copyright (C) 2016-2020 Three Mouse Technology, LLC and DictationBridge contributors
 * Copyright (C) 2026 Derek Lane and DictationBridge Lite contributors
 * SPDX-License-Identifier: MPL-2.0
 */

#include <windows.h>

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "protocol.h"

namespace {

HMODULE g_module = nullptr;
ATOM g_windowClass = 0;
HWND g_window = nullptr;
dbl::TextCallback g_insertedCallback = nullptr;
dbl::TextCallback g_deletedCallback = nullptr;
dbl::DebugCallback g_debugCallback = nullptr;
std::vector<HANDLE> g_loaderProcesses;

void debugLog(const char* message) {
	if (g_debugCallback) {
		g_debugCallback(message);
	}
}

LRESULT CALLBACK windowProc(HWND window, UINT message, WPARAM wParam, LPARAM lParam) {
	if (message != WM_COPYDATA) {
		return DefWindowProcW(window, message, wParam, lParam);
	}

	const auto* copyData = reinterpret_cast<const COPYDATASTRUCT*>(lParam);
	if (!copyData || !copyData->lpData) {
		return FALSE;
	}

	const auto kind = static_cast<dbl::MessageKind>(copyData->dwData);
	if (kind == dbl::MessageKind::debugLog) {
		if (g_debugCallback && copyData->cbData > 0) {
			std::string messageText(
				reinterpret_cast<const char*>(copyData->lpData),
				copyData->cbData);
			g_debugCallback(messageText.c_str());
		}
		return TRUE;
	}

	if (kind != dbl::MessageKind::textInserted && kind != dbl::MessageKind::textDeleted) {
		return FALSE;
	}
	if (copyData->cbData < sizeof(dbl::TextPayloadHeader)) {
		return FALSE;
	}

	const auto* header = reinterpret_cast<const dbl::TextPayloadHeader*>(copyData->lpData);
	const std::size_t availableTextBytes = copyData->cbData - sizeof(dbl::TextPayloadHeader);
	if (header->textLength > availableTextBytes / sizeof(wchar_t)) {
		return FALSE;
	}

	const auto* textStart = reinterpret_cast<const wchar_t*>(
		reinterpret_cast<const BYTE*>(copyData->lpData) + sizeof(dbl::TextPayloadHeader));
	std::wstring text(textStart, header->textLength);
	const auto callback = kind == dbl::MessageKind::textInserted
		? g_insertedCallback
		: g_deletedCallback;
	if (callback) {
		callback(header->windowHandle, header->startPosition, text.c_str());
	}
	return TRUE;
}

std::wstring siblingPath(const wchar_t* fileName) {
	wchar_t modulePath[MAX_PATH]{};
	const DWORD length = GetModuleFileNameW(g_module, modulePath, ARRAYSIZE(modulePath));
	if (length == 0 || length >= ARRAYSIZE(modulePath)) {
		return {};
	}
	std::wstring path(modulePath, length);
	const auto separator = path.find_last_of(L"\\/");
	if (separator == std::wstring::npos) {
		return {};
	}
	path.resize(separator + 1);
	path.append(fileName);
	return path;
}

bool startLoader(const wchar_t* fileName) {
	const std::wstring path = siblingPath(fileName);
	if (path.empty() || GetFileAttributesW(path.c_str()) == INVALID_FILE_ATTRIBUTES) {
		return false;
	}

	STARTUPINFOW startupInfo{};
	startupInfo.cb = sizeof(startupInfo);
	PROCESS_INFORMATION processInfo{};
	if (!CreateProcessW(
		path.c_str(),
		nullptr,
		nullptr,
		nullptr,
		FALSE,
		CREATE_NO_WINDOW,
		nullptr,
		nullptr,
		&startupInfo,
		&processInfo)) {
		return false;
	}
	CloseHandle(processInfo.hThread);
	if (WaitForSingleObject(processInfo.hProcess, 200) == WAIT_OBJECT_0) {
		CloseHandle(processInfo.hProcess);
		return false;
	}
	g_loaderProcesses.push_back(processInfo.hProcess);
	return true;
}

#ifndef _WIN64
bool is64BitWindows() {
	BOOL wow64 = FALSE;
	return IsWow64Process(GetCurrentProcess(), &wow64) && wow64;
}
#endif

void allowIpc() {
	using ChangeWindowMessageFilterExType = BOOL(WINAPI*)(HWND, UINT, DWORD, PCHANGEFILTERSTRUCT);
	const HMODULE user32 = GetModuleHandleW(L"user32.dll");
	const auto changeFilter = reinterpret_cast<ChangeWindowMessageFilterExType>(
		GetProcAddress(user32, "ChangeWindowMessageFilterEx"));
	if (changeFilter) {
		changeFilter(g_window, WM_COPYDATA, MSGFLT_ALLOW, nullptr);
	}
}

} // namespace

extern "C" __declspec(dllexport) void WINAPI DBL_SetTextInsertedCallback(dbl::TextCallback callback) {
	g_insertedCallback = callback;
}

extern "C" __declspec(dllexport) void WINAPI DBL_SetTextDeletedCallback(dbl::TextCallback callback) {
	g_deletedCallback = callback;
}

extern "C" __declspec(dllexport) void WINAPI DBL_SetDebugLogCallback(dbl::DebugCallback callback) {
	g_debugCallback = callback;
}

extern "C" __declspec(dllexport) BOOL WINAPI DBL_Start() {
	if (g_window) {
		return TRUE;
	}

	WNDCLASSEXW windowClass{};
	windowClass.cbSize = sizeof(windowClass);
	windowClass.lpfnWndProc = windowProc;
	windowClass.hInstance = g_module;
	windowClass.lpszClassName = dbl::kMasterWindowClass;
	g_windowClass = RegisterClassExW(&windowClass);
	if (!g_windowClass) {
		debugLog("Unable to register the DictationBridge Lite message window.");
		return FALSE;
	}

	g_window = CreateWindowExW(
		0,
		dbl::kMasterWindowClass,
		L"DictationBridge Lite Master",
		0,
		0,
		0,
		0,
		0,
		HWND_MESSAGE,
		nullptr,
		g_module,
		nullptr);
	if (!g_window) {
		UnregisterClassW(dbl::kMasterWindowClass, g_module);
		g_windowClass = 0;
		debugLog("Unable to create the DictationBridge Lite message window.");
		return FALSE;
	}
	allowIpc();

	bool sameArchitectureStarted = false;
#ifdef _WIN64
	sameArchitectureStarted = startLoader(L"DictationBridgeLiteLoader64.exe");
	if (!startLoader(L"DictationBridgeLiteLoader32.exe")) {
		debugLog("The 32-bit loader did not start; 32-bit applications will not be observed.");
	}
#else
	sameArchitectureStarted = startLoader(L"DictationBridgeLiteLoader32.exe");
	if (is64BitWindows() && !startLoader(L"DictationBridgeLiteLoader64.exe")) {
		debugLog("The 64-bit loader did not start; 64-bit applications will not be observed.");
	}
#endif
	if (!sameArchitectureStarted) {
		debugLog("Unable to start the same-architecture DictationBridge Lite loader.");
		DestroyWindow(g_window);
		g_window = nullptr;
		UnregisterClassW(dbl::kMasterWindowClass, g_module);
		g_windowClass = 0;
		return FALSE;
	}
	return TRUE;
}

extern "C" __declspec(dllexport) void WINAPI DBL_Stop() {
	if (g_window) {
		DestroyWindow(g_window);
		g_window = nullptr;
	}
	if (g_windowClass) {
		UnregisterClassW(dbl::kMasterWindowClass, g_module);
		g_windowClass = 0;
	}
	for (const HANDLE process : g_loaderProcesses) {
		WaitForSingleObject(process, 2000);
		CloseHandle(process);
	}
	g_loaderProcesses.clear();
}

BOOL WINAPI DllMain(HMODULE module, DWORD reason, LPVOID) {
	if (reason == DLL_PROCESS_ATTACH) {
		g_module = module;
		DisableThreadLibraryCalls(module);
	}
	return TRUE;
}
