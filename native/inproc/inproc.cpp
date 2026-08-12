/* Copyright (C) 2016-2020 Three Mouse Technology, LLC and DictationBridge contributors
 * Copyright (C) 2026 Derek Lane and DictationBridge Lite contributors
 * SPDX-License-Identifier: MPL-2.0
 */

#include <windows.h>
#include <msctf.h>
#include <MinHook.h>

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cwchar>
#include <cstring>
#include <string>
#include <vector>

#include "protocol.h"

namespace {

HMODULE g_module = nullptr;
HMODULE g_selfPin = nullptr;
CRITICAL_SECTION g_stateLock;
CRITICAL_SECTION g_hookLock;
std::atomic<long> g_threadsIn{0};
std::atomic<bool> g_active{false};
std::atomic<bool> g_unloading{false};
DWORD g_suspensionTls = TLS_OUT_OF_INDEXES;
HWINEVENTHOOK g_foregroundHook = nullptr;
HWINEVENTHOOK g_focusHook = nullptr;

struct ThreadIn {
	ThreadIn() { g_threadsIn.fetch_add(1, std::memory_order_acq_rel); }
	~ThreadIn() { g_threadsIn.fetch_sub(1, std::memory_order_acq_rel); }
};

struct HookSuspension {
	HookSuspension() {
		if (g_suspensionTls == TLS_OUT_OF_INDEXES) {
			return;
		}
		const auto current = reinterpret_cast<UINT_PTR>(TlsGetValue(g_suspensionTls));
		TlsSetValue(g_suspensionTls, reinterpret_cast<void*>(current + 1));
	}
	~HookSuspension() {
		if (g_suspensionTls == TLS_OUT_OF_INDEXES) {
			return;
		}
		const auto current = reinterpret_cast<UINT_PTR>(TlsGetValue(g_suspensionTls));
		TlsSetValue(g_suspensionTls, reinterpret_cast<void*>(current > 0 ? current - 1 : 0));
	}
};

bool hooksActive() {
	return g_active.load(std::memory_order_acquire)
		&& !g_unloading.load(std::memory_order_acquire)
		&& (g_suspensionTls == TLS_OUT_OF_INDEXES || TlsGetValue(g_suspensionTls) == nullptr);
}

HWND masterWindow() {
	return FindWindowExW(HWND_MESSAGE, nullptr, dbl::kMasterWindowClass, nullptr);
}

bool masterRunning() {
	return masterWindow() != nullptr;
}

void sendTextEvent(
	dbl::MessageKind kind,
	HWND window,
	std::int32_t startPosition,
	const wchar_t* text,
	std::uint32_t textLength) {
	if (!text || textLength == 0) {
		return;
	}
	const HWND master = masterWindow();
	if (!master) {
		return;
	}

	const std::size_t payloadSize = sizeof(dbl::TextPayloadHeader)
		+ static_cast<std::size_t>(textLength) * sizeof(wchar_t);
	std::vector<BYTE> payload(payloadSize);
	auto* header = reinterpret_cast<dbl::TextPayloadHeader*>(payload.data());
	header->windowHandle = reinterpret_cast<std::uint64_t>(window);
	header->startPosition = startPosition;
	header->textLength = textLength;
	std::memcpy(
		payload.data() + sizeof(dbl::TextPayloadHeader),
		text,
		static_cast<std::size_t>(textLength) * sizeof(wchar_t));

	COPYDATASTRUCT copyData{};
	copyData.dwData = static_cast<ULONG_PTR>(kind);
	copyData.cbData = static_cast<DWORD>(payload.size());
	copyData.lpData = payload.data();
	DWORD_PTR result = 0;
	SendMessageTimeoutW(master, WM_COPYDATA, 0, reinterpret_cast<LPARAM>(&copyData), SMTO_ABORTIFHUNG, 1000, &result);
}

struct HookRecord {
	void* target = nullptr;
	void* detour = nullptr;
	void** original = nullptr;
	HMODULE targetModule = nullptr;
	bool installed = false;
};

using InsertTextAtSelectionType = HRESULT(STDMETHODCALLTYPE*)(
	ITfInsertAtSelection*, TfEditCookie, DWORD, const WCHAR*, LONG, ITfRange**);
using SetTextType = HRESULT(STDMETHODCALLTYPE*)(ITfRange*, TfEditCookie, DWORD, const WCHAR*, LONG);

InsertTextAtSelectionType g_originalInsertTextAtSelection = nullptr;
SetTextType g_originalSetText = nullptr;
HookRecord g_insertHook;
HookRecord g_setTextHook;

bool installHook(HookRecord& hook, void* target, void* detour, void** original) {
	EnterCriticalSection(&g_hookLock);
	if (hook.installed) {
		const bool sameTarget = hook.target == target;
		LeaveCriticalSection(&g_hookLock);
		return sameTarget;
	}
	if (hook.target && hook.target != target) {
		LeaveCriticalSection(&g_hookLock);
		return false;
	}

	hook.target = target;
	hook.detour = detour;
	hook.original = original;
	if (!hook.targetModule) {
		GetModuleHandleExW(
			GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,
			reinterpret_cast<LPCWSTR>(target),
			&hook.targetModule);
	}
	const MH_STATUS createStatus = MH_CreateHook(target, detour, original);
	const bool created = createStatus == MH_OK || createStatus == MH_ERROR_ALREADY_CREATED;
	const MH_STATUS enableStatus = created ? MH_EnableHook(target) : createStatus;
	hook.installed = created && (enableStatus == MH_OK || enableStatus == MH_ERROR_ENABLED);
	const bool installed = hook.installed;
	LeaveCriticalSection(&g_hookLock);
	return installed;
}

void removeHook(HookRecord& hook) {
	if (!hook.installed || !hook.target) {
		return;
	}
	MH_DisableHook(hook.target);
	MH_RemoveHook(hook.target);
	hook.installed = false;
	hook.target = nullptr;
	if (hook.targetModule) {
		FreeLibrary(hook.targetModule);
		hook.targetModule = nullptr;
	}
}

void removeAllHooks() {
	EnterCriticalSection(&g_hookLock);
	removeHook(g_setTextHook);
	removeHook(g_insertHook);
	LeaveCriticalSection(&g_hookLock);
}

void getRangeLocation(ITfRange* range, HWND& window, LONG& startPosition) {
	window = GetFocus();
	startPosition = -1;
	if (!range) {
		return;
	}
	ITfContext* context = nullptr;
	if (SUCCEEDED(range->GetContext(&context)) && context) {
		ITfContextView* view = nullptr;
		if (SUCCEEDED(context->GetActiveView(&view)) && view) {
			view->GetWnd(&window);
			view->Release();
		}
		context->Release();
	}
	ITfRangeACP* rangeAcp = nullptr;
	if (SUCCEEDED(range->QueryInterface(IID_ITfRangeACP, reinterpret_cast<void**>(&rangeAcp))) && rangeAcp) {
		LONG length = 0;
		if (FAILED(rangeAcp->GetExtent(&startPosition, &length))) {
			startPosition = -1;
		}
		rangeAcp->Release();
	}
}

void* comMethodAddress(void* interfacePointer, std::size_t methodIndex) {
	return (*reinterpret_cast<void***>(interfacePointer))[methodIndex];
}

void hookRange(ITfRange* range);

HRESULT STDMETHODCALLTYPE detourInsertTextAtSelection(
	ITfInsertAtSelection* self,
	TfEditCookie editCookie,
	DWORD flags,
	const WCHAR* text,
	LONG textLength,
	ITfRange** outputRange) {
	ThreadIn threadIn;
	if (!hooksActive()) {
		return g_originalInsertTextAtSelection(self, editCookie, flags, text, textLength, outputRange);
	}
	HookSuspension suspension;
	const HRESULT result = g_originalInsertTextAtSelection(
		self, editCookie, flags, text, textLength, outputRange);
	const LONG resolvedTextLength = textLength < 0 && text
		? static_cast<LONG>(wcslen(text))
		: textLength;
	if (SUCCEEDED(result) && text && resolvedTextLength > 0) {
		ITfRange* range = outputRange ? *outputRange : nullptr;
		if (range) {
			hookRange(range);
		}
		HWND window = nullptr;
		LONG startPosition = -1;
		getRangeLocation(range, window, startPosition);
		sendTextEvent(
			dbl::MessageKind::textInserted,
			window,
			startPosition,
			text,
			static_cast<std::uint32_t>(resolvedTextLength));
	}
	return result;
}

HRESULT STDMETHODCALLTYPE detourSetText(
	ITfRange* self,
	TfEditCookie editCookie,
	DWORD flags,
	const WCHAR* text,
	LONG textLength) {
	ThreadIn threadIn;
	if (!hooksActive()) {
		return g_originalSetText(self, editCookie, flags, text, textLength);
	}
	HookSuspension suspension;
	HWND window = nullptr;
	LONG startPosition = -1;
	getRangeLocation(self, window, startPosition);

	std::vector<wchar_t> oldText(4096);
	ULONG oldTextLength = 0;
	const HRESULT readResult = self->GetText(
		editCookie,
		0,
		oldText.data(),
		static_cast<ULONG>(oldText.size()),
		&oldTextLength);
	const HRESULT result = g_originalSetText(self, editCookie, flags, text, textLength);
	const LONG resolvedTextLength = textLength < 0 && text
		? static_cast<LONG>(wcslen(text))
		: textLength;
	if (SUCCEEDED(result)) {
		if (SUCCEEDED(readResult) && oldTextLength > 0) {
			sendTextEvent(
				dbl::MessageKind::textDeleted,
				window,
				startPosition,
				oldText.data(),
				oldTextLength);
		}
		if (text && resolvedTextLength > 0) {
			sendTextEvent(
				dbl::MessageKind::textInserted,
				window,
				startPosition,
				text,
				static_cast<std::uint32_t>(resolvedTextLength));
		}
	}
	return result;
}

void hookInsertAtSelection(ITfInsertAtSelection* insertAtSelection) {
	if (!insertAtSelection) {
		return;
	}
	// IUnknown contributes the first three vtable entries. InsertTextAtSelection
	// is the first method declared by ITfInsertAtSelection.
	void* target = comMethodAddress(insertAtSelection, 3);
	installHook(
		g_insertHook,
		target,
		reinterpret_cast<void*>(&detourInsertTextAtSelection),
		reinterpret_cast<void**>(&g_originalInsertTextAtSelection));
}

void hookRange(ITfRange* range) {
	if (!range) {
		return;
	}
	// ITfRange declares GetText and then SetText after the three IUnknown entries.
	void* target = comMethodAddress(range, 4);
	installHook(
		g_setTextHook,
		target,
		reinterpret_cast<void*>(&detourSetText),
		reinterpret_cast<void**>(&g_originalSetText));
}

void hookFocusedContext() {
	if (!hooksActive()) {
		return;
	}

	ITfThreadMgr* threadManager = nullptr;
	if (FAILED(CoCreateInstance(
		CLSID_TF_ThreadMgr,
		nullptr,
		CLSCTX_INPROC_SERVER,
		IID_ITfThreadMgr,
		reinterpret_cast<void**>(&threadManager))) || !threadManager) {
		return;
	}
	ITfDocumentMgr* documentManager = nullptr;
	if (SUCCEEDED(threadManager->GetFocus(&documentManager)) && documentManager) {
		ITfContext* context = nullptr;
		if (SUCCEEDED(documentManager->GetBase(&context)) && context) {
			ITfInsertAtSelection* insertAtSelection = nullptr;
			if (SUCCEEDED(context->QueryInterface(
				IID_ITfInsertAtSelection,
				reinterpret_cast<void**>(&insertAtSelection))) && insertAtSelection) {
				hookInsertAtSelection(insertAtSelection);
				insertAtSelection->Release();
			}
			context->Release();
		}
		documentManager->Release();
	}
	threadManager->Release();
}

DWORD WINAPI unloadMonitor(void*) {
	while (masterRunning()) {
		Sleep(127);
	}
	g_unloading.store(true, std::memory_order_release);
	g_active.store(false, std::memory_order_release);
	while (g_threadsIn.load(std::memory_order_acquire) > 0) {
		Sleep(10);
	}
	removeAllHooks();
	MH_Uninitialize();
	if (g_suspensionTls != TLS_OUT_OF_INDEXES) {
		TlsFree(g_suspensionTls);
		g_suspensionTls = TLS_OUT_OF_INDEXES;
	}
	if (g_selfPin) {
		const HMODULE selfPin = g_selfPin;
		g_selfPin = nullptr;
		FreeLibraryAndExitThread(selfPin, 0);
	}
	return 0;
}

} // namespace

extern "C" __declspec(dllexport) DWORD WINAPI Attach() {
	EnterCriticalSection(&g_stateLock);
	if (g_unloading.load(std::memory_order_acquire)) {
		LeaveCriticalSection(&g_stateLock);
		return ERROR_SHUTDOWN_IN_PROGRESS;
	}
	if (g_active.load(std::memory_order_acquire)) {
		LeaveCriticalSection(&g_stateLock);
		return ERROR_SUCCESS;
	}
	if (MH_Initialize() != MH_OK) {
		LeaveCriticalSection(&g_stateLock);
		return ERROR_DLL_INIT_FAILED;
	}
	g_suspensionTls = TlsAlloc();
	if (g_suspensionTls == TLS_OUT_OF_INDEXES) {
		MH_Uninitialize();
		LeaveCriticalSection(&g_stateLock);
		return ERROR_NOT_ENOUGH_MEMORY;
	}

	wchar_t modulePath[MAX_PATH]{};
	if (!GetModuleFileNameW(g_module, modulePath, ARRAYSIZE(modulePath))) {
		TlsFree(g_suspensionTls);
		g_suspensionTls = TLS_OUT_OF_INDEXES;
		MH_Uninitialize();
		LeaveCriticalSection(&g_stateLock);
		return GetLastError();
	}
	g_selfPin = LoadLibraryW(modulePath);
	if (!g_selfPin) {
		TlsFree(g_suspensionTls);
		g_suspensionTls = TLS_OUT_OF_INDEXES;
		MH_Uninitialize();
		LeaveCriticalSection(&g_stateLock);
		return GetLastError();
	}
	g_active.store(true, std::memory_order_release);
	const HANDLE monitor = CreateThread(nullptr, 0, unloadMonitor, nullptr, 0, nullptr);
	if (!monitor) {
		const DWORD error = GetLastError();
		g_active.store(false, std::memory_order_release);
		FreeLibrary(g_selfPin);
		g_selfPin = nullptr;
		TlsFree(g_suspensionTls);
		g_suspensionTls = TLS_OUT_OF_INDEXES;
		MH_Uninitialize();
		LeaveCriticalSection(&g_stateLock);
		return error;
	}
	CloseHandle(monitor);
	LeaveCriticalSection(&g_stateLock);
	return ERROR_SUCCESS;
}

extern "C" void CALLBACK WinEventProc(
	HWINEVENTHOOK,
	DWORD,
	HWND,
	LONG,
	LONG,
	DWORD eventThread,
	DWORD) {
	ThreadIn threadIn;
	if (eventThread != GetCurrentThreadId()) {
		return;
	}
	if (!g_active.load(std::memory_order_acquire) && Attach() != ERROR_SUCCESS) {
		return;
	}
	hookFocusedContext();
}

extern "C" __declspec(dllexport) BOOL WINAPI InstallHooks() {
	g_foregroundHook = SetWinEventHook(
		EVENT_SYSTEM_FOREGROUND,
		EVENT_SYSTEM_FOREGROUND,
		g_module,
		WinEventProc,
		0,
		0,
		WINEVENT_INCONTEXT);
	if (!g_foregroundHook) {
		return FALSE;
	}
	g_focusHook = SetWinEventHook(
		EVENT_OBJECT_FOCUS,
		EVENT_OBJECT_FOCUS,
		g_module,
		WinEventProc,
		0,
		0,
		WINEVENT_INCONTEXT);
	if (!g_focusHook) {
		UnhookWinEvent(g_foregroundHook);
		g_foregroundHook = nullptr;
		return FALSE;
	}
	return TRUE;
}

extern "C" __declspec(dllexport) void WINAPI RemoveHooks() {
	if (g_focusHook) {
		UnhookWinEvent(g_focusHook);
		g_focusHook = nullptr;
	}
	if (g_foregroundHook) {
		UnhookWinEvent(g_foregroundHook);
		g_foregroundHook = nullptr;
	}
}

BOOL WINAPI DllMain(HMODULE module, DWORD reason, LPVOID) {
	if (reason == DLL_PROCESS_ATTACH) {
		g_module = module;
		InitializeCriticalSection(&g_stateLock);
		InitializeCriticalSection(&g_hookLock);
		DisableThreadLibraryCalls(module);
	} else if (reason == DLL_PROCESS_DETACH) {
		DeleteCriticalSection(&g_hookLock);
		DeleteCriticalSection(&g_stateLock);
	}
	return TRUE;
}
