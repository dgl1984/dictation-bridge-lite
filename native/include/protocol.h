/* Copyright (C) 2016-2020 Three Mouse Technology, LLC and DictationBridge contributors
 * Copyright (C) 2026 Derek Lane and DictationBridge Lite contributors
 * SPDX-License-Identifier: MPL-2.0
 */

#pragma once

#include <cstdint>
#include <windows.h>

namespace dbl {

inline constexpr wchar_t kMasterWindowClass[] = L"DictationBridgeLiteMaster";

enum class MessageKind : ULONG_PTR {
	textInserted = 1,
	textDeleted = 2,
	debugLog = 3,
};

#pragma pack(push, 1)
struct TextPayloadHeader {
	std::uint64_t windowHandle;
	std::int32_t startPosition;
	std::uint32_t textLength;
};
#pragma pack(pop)

static_assert(sizeof(TextPayloadHeader) == 16, "The cross-architecture IPC header must remain fixed-width.");

using TextCallback = void(CALLBACK*)(
	std::uint64_t windowHandle,
	std::int32_t startPosition,
	LPCWSTR text);
using DebugCallback = void(CALLBACK*)(LPCSTR message);

} // namespace dbl
