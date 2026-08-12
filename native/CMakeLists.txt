# Copyright (C) 2026 Derek Lane and DictationBridge Lite contributors
# SPDX-License-Identifier: MPL-2.0

cmake_minimum_required(VERSION 3.21)
project(DictationBridgeLiteNative LANGUAGES C CXX)

if(NOT WIN32)
	message(FATAL_ERROR "DictationBridge Lite native components must be built for Windows.")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

if(CMAKE_SIZEOF_VOID_P EQUAL 8)
	set(DBL_ARCH_SUFFIX 64)
	set(MINHOOK_HDE_SOURCE third_party/minhook/src/hde/hde64.c)
else()
	set(DBL_ARCH_SUFFIX 32)
	set(MINHOOK_HDE_SOURCE third_party/minhook/src/hde/hde32.c)
endif()

add_library(minhook STATIC
	third_party/minhook/src/buffer.c
	third_party/minhook/src/hook.c
	third_party/minhook/src/trampoline.c
	${MINHOOK_HDE_SOURCE}
)
target_include_directories(minhook PUBLIC
	third_party/minhook/include
	third_party/minhook/src
	third_party/minhook/src/hde
)

add_library(dbl_inproc SHARED inproc/inproc.cpp inproc/inproc.def)
target_include_directories(dbl_inproc PRIVATE include)
target_link_libraries(dbl_inproc PRIVATE minhook user32 ole32 uuid)
set_target_properties(dbl_inproc PROPERTIES
	OUTPUT_NAME "DictationBridgeLiteInproc${DBL_ARCH_SUFFIX}"
)

add_executable(dbl_loader WIN32 loader/loader.cpp)
target_include_directories(dbl_loader PRIVATE include)
target_link_libraries(dbl_loader PRIVATE dbl_inproc user32)
set_target_properties(dbl_loader PROPERTIES
	OUTPUT_NAME "DictationBridgeLiteLoader${DBL_ARCH_SUFFIX}"
)

add_library(dbl_master SHARED master/master.cpp master/master.def)
target_include_directories(dbl_master PRIVATE include)
target_link_libraries(dbl_master PRIVATE user32)
set_target_properties(dbl_master PROPERTIES
	OUTPUT_NAME "DictationBridgeLiteMaster${DBL_ARCH_SUFFIX}"
)

foreach(target dbl_inproc dbl_loader dbl_master)
	if(MSVC)
		target_compile_options(${target} PRIVATE /W4 /WX /guard:cf)
		target_link_options(${target} PRIVATE /DYNAMICBASE /NXCOMPAT /guard:cf)
	endif()
endforeach()

if(MSVC)
	target_compile_options(minhook PRIVATE /guard:cf)
endif()

foreach(target dbl_inproc dbl_loader dbl_master)
	set_target_properties(${target} PROPERTIES
		RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
		LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
		RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
		LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
	)
endforeach()
