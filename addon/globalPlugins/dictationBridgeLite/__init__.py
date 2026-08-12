# Copyright (C) 2026 Derek Lane and DictationBridge Lite contributors
# SPDX-License-Identifier: GPL-2.0-only

"""NVDA integration for DictationBridge Lite.

The preferred backend receives inserted and deleted text from the native
Text Services Framework observer. A Python-only typed-character fallback is
kept so the same add-on package can be used as a compatibility probe before
the native components are built.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from ctypes import wintypes

import addonHandler
import api
import braille
import controlTypes
import eventHandler
import gui
import inputCore
import queueHandler
import speech
import textInfos
import ui
import winUser
import wx
from NVDAObjects import NVDAObject
from globalPluginHandler import GlobalPlugin as BaseGlobalPlugin
from logHandler import log
from scriptHandler import script


addonHandler.initTranslation()

ADDON_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ECHO_DELAY_MS = 100
PHYSICAL_KEY_GRACE_SECONDS = 0.35
NATIVE_TYPED_DEDUP_SECONDS = 1.0
FALLBACK_DEDUP_SECONDS = 1.0
ONLINE_COMPOSITION_GRACE_SECONDS = 4.0
ONLINE_SPEECH_DEDUP_SECONDS = 2.0
WSR_EVENT_REQUEST_RETRY_SECONDS = 1.0
WSR_PANEL_DEDUP_SECONDS = 0.5
WSR_PANEL_REFRESH_DELAY_MS = 250
MAX_TEXT_SNAPSHOTS = 32
ONLINE_SPEECH_SETTINGS_URI = "ms-settings:privacy-speech"
OFFLINE_SPEECH_CONTROL_COMMAND = (
	"control",
	"/name",
	"Microsoft.SpeechRecognition",
)

TextCallbackType = ctypes.WINFUNCTYPE(
	None,
	ctypes.c_uint64,
	ctypes.c_int32,
	ctypes.c_wchar_p,
)
DebugCallbackType = ctypes.WINFUNCTYPE(None, ctypes.c_char_p)


class WSRAlternatesPanel(NVDAObject):
	"""The legacy Windows Speech Recognition correction choices dialog."""


class WSRSpellingPanel(NVDAObject):
	"""The legacy Windows Speech Recognition spelling dialog."""


class GlobalPlugin(BaseGlobalPlugin):
	"""Echo text entered by Windows voice typing."""

	scriptCategory = _("DictationBridge Lite")

	def __init__(self):
		super().__init__()
		self._enabled = True
		self._pendingStart: int | None = None
		self._pendingText = ""
		self._flushTimer: wx.CallLater | None = None
		self._lastPhysicalKeyTime = 0.0
		self._nativeDedupText = ""
		self._nativeDedupTime = 0.0
		self._nativeDeletedDedupText = ""
		self._nativeDeletedDedupTime = 0.0
		self._fallbackDedupText = ""
		self._fallbackDedupTime = 0.0
		self._fallbackDeletedDedupText = ""
		self._fallbackDeletedDedupTime = 0.0
		self._textSnapshots = {}
		self._wsrRequestedPid = None
		self._lastWSRRequestTime = 0.0
		self._lastWSRPanelKey = None
		self._lastWSRPanelTime = 0.0
		self._lastWSRSelectionKey = None
		self._lastWSRSelectionTime = 0.0
		self._wsrPanelObject = None
		self._lastWSRFeedback = ""
		self._lastOnlineCompositionTime = 0.0
		self._onlineSpeechDedupUntil = 0.0
		self._recentOnlineSpeech = {}
		self._rawKeyHandlerRegistered = False
		self._speechFilter = None
		self._speechFilterRegistered = False
		self._toolsSubmenu = None
		self._toolsMenuEntry = None
		self._onlineSettingsMenuItem = None
		self._offlineSettingsMenuItem = None
		self._echoMenuItem = None
		self._native = None
		self._nativeActive = False
		self._textInsertedCallback = TextCallbackType(self._nativeTextInserted)
		self._textDeletedCallback = TextCallbackType(self._nativeTextDeleted)
		self._debugCallback = DebugCallbackType(self._nativeDebugLog)
		self._registerRawKeyObserver()
		self._registerSpeechFilter()
		self._startNativeBackend()
		self._snapshotObject(api.getFocusObject())
		self._requestWSRPanelEvents()
		self._createToolsMenu()

	def _registerRawKeyObserver(self):
		observer = getattr(inputCore, "decide_handleRawKey", None)
		if observer is None:
			log.warning("DictationBridge Lite: raw-key observer is unavailable")
			return
		try:
			observer.register(self._observeRawKey)
			self._rawKeyHandlerRegistered = True
		except Exception:
			log.exception("DictationBridge Lite: unable to register raw-key observer")

	def _observeRawKey(self, vkCode, scanCode, extended, pressed):
		if pressed:
			self._lastPhysicalKeyTime = time.monotonic()
		return True

	def _registerSpeechFilter(self):
		"""Suppress only exact, rapid repeats of a finalized online phrase."""
		try:
			observer = getattr(speech, "filter_speechSequence", None)
			if observer is None:
				return
			observer.register(self._filterOnlineDuplicateSpeech)
			self._speechFilter = observer
			self._speechFilterRegistered = True
		except Exception:
			log.exception("DictationBridge Lite: unable to register online speech filter")

	def _filterOnlineDuplicateSpeech(self, speechSequence):
		now = time.monotonic()
		if now > self._onlineSpeechDedupUntil:
			self._recentOnlineSpeech.clear()
			return speechSequence
		text = " ".join(item for item in speechSequence if isinstance(item, str)).strip()
		if not text:
			return speechSequence
		lastTime = self._recentOnlineSpeech.get(text)
		self._recentOnlineSpeech[text] = now
		if lastTime is not None and now - lastTime <= ONLINE_SPEECH_DEDUP_SECONDS:
			return []
		return speechSequence

	def _createToolsMenu(self):
		"""Add discoverable Windows dictation controls to NVDA's Tools menu."""
		try:
			trayIcon = gui.mainFrame.sysTrayIcon
			self._toolsSubmenu = wx.Menu()
			self._onlineSettingsMenuItem = self._toolsSubmenu.Append(
				wx.ID_ANY,
				_("&Online dictation settings..."),
				_("Open Windows online speech-recognition privacy settings."),
			)
			self._offlineSettingsMenuItem = self._toolsSubmenu.Append(
				wx.ID_ANY,
				_("O&ffline Speech Recognition settings..."),
				_("Open the legacy Windows Speech Recognition Control Panel."),
			)
			self._toolsSubmenu.AppendSeparator()
			self._echoMenuItem = self._toolsSubmenu.Append(
				wx.ID_ANY,
				_("&Speak dictated text"),
				_("Enable or disable DictationBridge Lite announcements."),
				kind=wx.ITEM_CHECK,
			)
			self._echoMenuItem.Check(self._enabled)
			self._toolsMenuEntry = trayIcon.toolsMenu.AppendSubMenu(
				self._toolsSubmenu,
				_("DictationBridge &Lite"),
				_("Open Windows dictation settings or control dictated-text announcements."),
			)
			trayIcon.Bind(wx.EVT_MENU, self._onOpenOnlineSettings, self._onlineSettingsMenuItem)
			trayIcon.Bind(wx.EVT_MENU, self._onOpenOfflineSettings, self._offlineSettingsMenuItem)
			trayIcon.Bind(wx.EVT_MENU, self._onToggleEchoMenu, self._echoMenuItem)
		except Exception:
			log.exception("DictationBridge Lite: unable to create NVDA Tools menu")
			self._removeToolsMenu()

	def _removeToolsMenu(self):
		"""Remove menu objects during add-on reload or NVDA shutdown."""
		try:
			trayIcon = gui.mainFrame.sysTrayIcon
			for item, handler in (
				(self._onlineSettingsMenuItem, self._onOpenOnlineSettings),
				(self._offlineSettingsMenuItem, self._onOpenOfflineSettings),
				(self._echoMenuItem, self._onToggleEchoMenu),
			):
				if item is not None:
					trayIcon.Unbind(wx.EVT_MENU, handler=handler, source=item)
			if self._toolsMenuEntry is not None:
				trayIcon.toolsMenu.Remove(self._toolsMenuEntry.Id)
				self._toolsMenuEntry.Destroy()
			if self._toolsSubmenu is not None:
				self._toolsSubmenu.Destroy()
		except Exception:
			log.debug("DictationBridge Lite: unable to remove NVDA Tools menu cleanly", exc_info=True)
		finally:
			self._toolsSubmenu = None
			self._toolsMenuEntry = None
			self._onlineSettingsMenuItem = None
			self._offlineSettingsMenuItem = None
			self._echoMenuItem = None

	def _onOpenOnlineSettings(self, event):
		if event is not None:
			event.Skip()
		try:
			os.startfile(ONLINE_SPEECH_SETTINGS_URI)
		except OSError:
			log.exception("DictationBridge Lite: unable to open online dictation settings")
			ui.message(_("Windows online dictation settings could not be opened"))

	def _onOpenOfflineSettings(self, event):
		if event is not None:
			event.Skip()
		try:
			subprocess.Popen(OFFLINE_SPEECH_CONTROL_COMMAND)
		except OSError:
			log.exception("DictationBridge Lite: unable to open offline Speech Recognition settings")
			ui.message(_("Windows offline Speech Recognition settings could not be opened"))

	def _setEchoEnabled(self, enabled):
		self._enabled = bool(enabled)
		if not self._enabled:
			self._cancelFlushTimer()
			self._pendingStart = None
			self._pendingText = ""
			self._nativeDedupText = ""
			self._nativeDeletedDedupText = ""
			self._fallbackDedupText = ""
			self._fallbackDeletedDedupText = ""
		if self._echoMenuItem is not None:
			self._echoMenuItem.Check(self._enabled)

	def _onToggleEchoMenu(self, event):
		if event is not None:
			event.Skip()
		self._setEchoEnabled(not self._enabled)
		ui.message(_("DictationBridge Lite echo on") if self._enabled else _("DictationBridge Lite echo off"))

	def _startNativeBackend(self):
		architecture = ctypes.sizeof(ctypes.c_void_p) * 8
		dllName = f"DictationBridgeLiteMaster{architecture}.dll"
		dllPath = os.path.join(ADDON_ROOT, dllName)
		if not os.path.isfile(dllPath):
			log.warning(
				"DictationBridge Lite: %s is absent; using Python-only compatibility mode",
				dllName,
			)
			return
		try:
			native = ctypes.WinDLL(dllPath)
			native.DBL_SetTextInsertedCallback.argtypes = [TextCallbackType]
			native.DBL_SetTextInsertedCallback.restype = None
			native.DBL_SetTextDeletedCallback.argtypes = [TextCallbackType]
			native.DBL_SetTextDeletedCallback.restype = None
			native.DBL_SetDebugLogCallback.argtypes = [DebugCallbackType]
			native.DBL_SetDebugLogCallback.restype = None
			native.DBL_Start.argtypes = []
			native.DBL_Start.restype = wintypes.BOOL
			native.DBL_Stop.argtypes = []
			native.DBL_Stop.restype = None
			native.DBL_SetTextInsertedCallback(self._textInsertedCallback)
			native.DBL_SetTextDeletedCallback(self._textDeletedCallback)
			native.DBL_SetDebugLogCallback(self._debugCallback)
			if not native.DBL_Start():
				raise ctypes.WinError()
			self._native = native
			self._nativeActive = True
			log.info("DictationBridge Lite: native %s-bit text observer started", architecture)
		except Exception:
			self._native = None
			self._nativeActive = False
			log.exception("DictationBridge Lite: native backend failed; using Python-only mode")

	def _nativeTextInserted(self, windowHandle, startPosition, text):
		if not text:
			return
		# A control can report its value change before the TSF callback reaches
		# this thread. In that ordering the value-change fallback has already
		# queued the text, so consume the later native report.
		if self._isDuplicateOfRecentFallbackInsertion(text):
			return
		# Some controls may expose the same TSF insertion to NVDA again as
		# synthetic typed-character events. Remember the native text briefly so
		# event_typedCharacter can consume that duplicate without disabling the
		# typed-character path needed by legacy offline WSR.
		self._nativeDedupText = text
		self._nativeDedupTime = time.monotonic()
		queueHandler.queueFunction(
			queueHandler.eventQueue,
			self._enqueueInsertion,
			int(startPosition),
			text,
		)

	def _nativeTextDeleted(self, windowHandle, startPosition, text):
		if not text:
			return
		if self._isDuplicateOfRecentFallbackDeletion(text):
			return
		self._nativeDeletedDedupText = text
		self._nativeDeletedDedupTime = time.monotonic()
		queueHandler.queueFunction(
			queueHandler.eventQueue,
			self._announceDeletion,
			text,
		)

	def _nativeDebugLog(self, message):
		if not message:
			return
		try:
			decoded = message.decode("utf-8", errors="replace")
		except AttributeError:
			decoded = str(message)
		log.debug("DictationBridge Lite native: %s", decoded)

	def _cancelFlushTimer(self):
		if self._flushTimer is not None:
			self._flushTimer.Stop()
			self._flushTimer = None

	def _scheduleFlush(self):
		self._cancelFlushTimer()
		self._flushTimer = wx.CallLater(ECHO_DELAY_MS, self._flushPending)

	def _enqueueInsertion(self, start: int, text: str):
		if not self._enabled or not text:
			return
		if self._pendingStart is None:
			self._pendingStart = start
			self._pendingText = text
			self._scheduleFlush()
			return

		previousStart = self._pendingStart
		previousText = self._pendingText
		if start == -1 and previousStart == -1:
			self._pendingText = previousText + text
		elif start >= 0 and previousStart >= 0:
			previousEnd = previousStart + len(previousText)
			if previousStart <= start <= previousEnd:
				offset = start - previousStart
				self._pendingText = previousText[:offset] + text
			else:
				self._flushPending()
				self._pendingStart = start
				self._pendingText = text
		else:
			self._flushPending()
			self._pendingStart = start
			self._pendingText = text
		self._scheduleFlush()

	def _flushPending(self):
		self._cancelFlushTimer()
		text = self._pendingText
		self._pendingStart = None
		self._pendingText = ""
		if not self._enabled or not text:
			return
		text = text.replace("\r\n", "\n").replace("\r", "\n")
		while "\n" in text:
			line, separator, remainder = text.partition("\n")
			if line:
				self._speakEcho(line)
			if remainder.startswith("\n"):
				self._speakEcho(_("new paragraph"))
				text = remainder[1:]
			else:
				self._speakEcho(_("new line"))
				text = remainder
		if text:
			self._speakEcho(text)
		try:
			braille.handler.handleCaretMove(api.getFocusObject())
		except Exception:
			log.debug("DictationBridge Lite: unable to refresh braille", exc_info=True)

	def _speakEcho(self, text: str):
		# Tooltips and other transient UI can cancel speech requested from the
		# event currently being handled. NVDA's delayed-message API moves this
		# announcement to the next core cycle and gives it NOW priority, so the
		# dictated text is not lost when suggestion UI appears at the same time.
		ui.delayedMessage(text, speechPriority=speech.Spri.NOW)

	def _announceDeletion(self, text: str):
		if not self._enabled or not text:
			return
		self._flushPending()
		cleaned = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
		self._speakEcho(_("deleted {text}").format(text=cleaned))

	def _isDuplicateOfRecentNativeInsertion(self, text: str) -> bool:
		if not self._nativeActive or not self._nativeDedupText:
			return False
		if time.monotonic() - self._nativeDedupTime > NATIVE_TYPED_DEDUP_SECONDS:
			self._nativeDedupText = ""
			return False
		if self._nativeDedupText.startswith(text):
			self._nativeDedupText = self._nativeDedupText[len(text):]
			return True
		if text.startswith(self._nativeDedupText):
			self._nativeDedupText = ""
			return True
		self._nativeDedupText = ""
		return False

	def _rememberFallbackInsertion(self, text: str):
		if not text:
			return
		now = time.monotonic()
		if (
			self._fallbackDedupText
			and now - self._fallbackDedupTime <= FALLBACK_DEDUP_SECONDS
		):
			self._fallbackDedupText += text
		else:
			self._fallbackDedupText = text
		self._fallbackDedupTime = now

	def _isDuplicateOfRecentFallbackInsertion(self, text: str) -> bool:
		if not self._fallbackDedupText:
			return False
		if time.monotonic() - self._fallbackDedupTime > FALLBACK_DEDUP_SECONDS:
			self._fallbackDedupText = ""
			return False
		if self._fallbackDedupText.startswith(text):
			self._fallbackDedupText = self._fallbackDedupText[len(text):]
			return True
		if text.startswith(self._fallbackDedupText):
			self._fallbackDedupText = ""
			return True
		self._fallbackDedupText = ""
		return False

	@staticmethod
	def _consumeRecentText(instance, text, textAttribute, timeAttribute, timeout):
		remembered = getattr(instance, textAttribute)
		if not remembered:
			return False
		if time.monotonic() - getattr(instance, timeAttribute) > timeout:
			setattr(instance, textAttribute, "")
			return False
		if remembered.startswith(text):
			setattr(instance, textAttribute, remembered[len(text):])
			return True
		if text.startswith(remembered):
			setattr(instance, textAttribute, "")
			return True
		setattr(instance, textAttribute, "")
		return False

	def _isDuplicateOfRecentNativeDeletion(self, text: str) -> bool:
		if not self._nativeActive:
			return False
		return self._consumeRecentText(
			self,
			text,
			"_nativeDeletedDedupText",
			"_nativeDeletedDedupTime",
			NATIVE_TYPED_DEDUP_SECONDS,
		)

	def _rememberFallbackDeletion(self, text: str):
		if not text:
			return
		self._fallbackDeletedDedupText = text
		self._fallbackDeletedDedupTime = time.monotonic()

	def _isDuplicateOfRecentFallbackDeletion(self, text: str) -> bool:
		return self._consumeRecentText(
			self,
			text,
			"_fallbackDeletedDedupText",
			"_fallbackDeletedDedupTime",
			FALLBACK_DEDUP_SECONDS,
		)

	@staticmethod
	def _objectKey(obj):
		if obj is None:
			return None
		windowHandle = int(getattr(obj, "windowHandle", 0) or 0)
		if windowHandle:
			key = (
				windowHandle,
				int(getattr(obj, "event_childID", 0) or 0),
			)
			# Windows online dictation exposes an interim object named
			# "Composition" with the same HWND and child ID as the real editor.
			# Keep its snapshot separate so it cannot replace the document state.
			if GlobalPlugin._isOnlineCompositionObject(obj):
				return key + ("onlineComposition",)
			return key
		return id(obj)

	@staticmethod
	def _isOnlineCompositionObject(obj):
		return (getattr(obj, "name", "") or "").casefold() == "composition"

	def _isRecentOnlineComposition(self):
		lastTime = getattr(self, "_lastOnlineCompositionTime", 0.0)
		return (
			lastTime != 0.0
			and time.monotonic() - lastTime
			<= ONLINE_COMPOSITION_GRACE_SECONDS
		)

	def _getEditableText(self, obj):
		if obj is None:
			return None
		try:
			focus = api.getFocusObject()
			if self._objectKey(obj) != self._objectKey(focus):
				return None
			states = getattr(obj, "states", set()) or set()
			if controlTypes.State.PROTECTED in states:
				return None
			if (
				getattr(obj, "role", None) != controlTypes.Role.EDITABLETEXT
				and controlTypes.State.EDITABLE not in states
			):
				return None
			text = obj.makeTextInfo(textInfos.POSITION_ALL).text
			return text if isinstance(text, str) else None
		except Exception:
			log.debug(
				"DictationBridge Lite: unable to read editable text snapshot",
				exc_info=True,
			)
			return None

	def _snapshotObject(self, obj):
		text = self._getEditableText(obj)
		if text is None:
			return
		key = self._objectKey(obj)
		self._textSnapshots[key] = text
		if len(self._textSnapshots) > MAX_TEXT_SNAPSHOTS:
			self._textSnapshots.pop(next(iter(self._textSnapshots)))

	@staticmethod
	def _diffText(oldText: str, newText: str):
		prefix = 0
		limit = min(len(oldText), len(newText))
		while prefix < limit and oldText[prefix] == newText[prefix]:
			prefix += 1

		suffix = 0
		oldRemaining = len(oldText) - prefix
		newRemaining = len(newText) - prefix
		while (
			suffix < oldRemaining
			and suffix < newRemaining
			and oldText[len(oldText) - suffix - 1] == newText[len(newText) - suffix - 1]
		):
			suffix += 1

		oldEnd = len(oldText) - suffix if suffix else len(oldText)
		newEnd = len(newText) - suffix if suffix else len(newText)
		return prefix, oldText[prefix:oldEnd], newText[prefix:newEnd]

	def event_gainFocus(self, obj, nextHandler):
		if self._isOnlineCompositionObject(obj):
			self._lastOnlineCompositionTime = time.monotonic()
		elif self._isRecentOnlineComposition() and (
			(getattr(obj, "name", "") or "").casefold() == "text editor"
		):
			# NVDA reads the finalized online phrase when focus returns from the
			# composition object. Limit duplicate filtering to this short window.
			self._onlineSpeechDedupUntil = (
				time.monotonic() + ONLINE_SPEECH_DEDUP_SECONDS
			)
			self._recentOnlineSpeech.clear()
		nextHandler()
		self._snapshotObject(obj)
		self._requestWSRPanelEvents()

	def _handleEditableChange(self, obj, nextHandler, source):
		try:
			key = self._objectKey(obj)
			oldText = self._textSnapshots.get(key)
			newText = self._getEditableText(obj)
			if newText is None:
				return
			self._textSnapshots[key] = newText
			if len(self._textSnapshots) > MAX_TEXT_SNAPSHOTS:
				self._textSnapshots.pop(next(iter(self._textSnapshots)))
			self._requestWSRPanelEvents()
			if self._isOnlineCompositionObject(obj):
				self._lastOnlineCompositionTime = time.monotonic()
				return
			if self._isRecentOnlineComposition() and (
				(getattr(obj, "name", "") or "").casefold() == "text editor"
			):
				# The completed phrase is already announced by NVDA when focus
				# returns to the editor. Do not also echo partial commit writes.
				return
			if (
				not self._enabled
				or self._wsrRequestedPid is None
				or oldText is None
				or oldText == newText
				or time.monotonic() - self._lastPhysicalKeyTime < PHYSICAL_KEY_GRACE_SECONDS
			):
				return

			start, deletedText, insertedText = self._diffText(oldText, newText)
			if deletedText:
				if not self._isDuplicateOfRecentNativeDeletion(deletedText):
					self._rememberFallbackDeletion(deletedText)
					self._announceDeletion(deletedText)
			if insertedText:
				if self._isDuplicateOfRecentNativeInsertion(insertedText):
					return
				self._rememberFallbackInsertion(insertedText)
				self._enqueueInsertion(start, insertedText)
		except Exception:
			log.exception("DictationBridge Lite: %s fallback failed", source)
		finally:
			nextHandler()

	def event_valueChange(self, obj, nextHandler):
		if self._handleWSRFeedback(obj):
			nextHandler()
			return
		self._handleEditableChange(obj, nextHandler, "valueChange")

	def event_textChange(self, obj, nextHandler):
		# UIA edit controls can report the same kind of document update as a
		# text-change event rather than the MSAA value-change event used by
		# classic Notepad. The shared snapshot makes receiving both harmless.
		self._handleEditableChange(obj, nextHandler, "textChange")

	def event_nameChange(self, obj, nextHandler):
		appModule = getattr(obj, "appModule", None)
		appName = (getattr(appModule, "appName", "") or "").casefold()
		if appName == "textinputhost":
			automationId = getattr(obj, "UIAAutomationId", None)
			name = (getattr(obj, "name", "") or "").strip().casefold()
			if automationId == "DictationHintControl":
				# Rotating tips interrupt every dictated phrase without adding
				# useful information for an experienced dictation user.
				return
			if automationId == "DictationStateErrorControl" and name in {
				"",
				"listening...",
				"thinking...",
			}:
				# Preserve genuine error text while silencing routine state churn.
				return
		nextHandler()

	def _handleWSRFeedback(self, obj):
		"""Announce actionable legacy WSR status and refresh reused panels."""
		if self._wsrRequestedPid is None:
			return False
		if int(getattr(obj, "processID", 0) or 0) != self._wsrRequestedPid:
			return False
		if getattr(obj, "windowClassName", "") != "MS:SpeechTopLevel":
			return False
		if (getattr(obj, "name", "") or "").casefold() != "speech recognition feedback":
			return False
		value = (getattr(obj, "value", "") or "").strip()
		if not value or value == self._lastWSRFeedback:
			return True
		self._lastWSRFeedback = value
		if value.casefold().startswith("correcting"):
			if self._wsrPanelObject is not None:
				wx.CallLater(
					WSR_PANEL_REFRESH_DELAY_MS,
					self._announceWSRPanel,
					self._wsrPanelObject,
					True,
				)
			return True
		if value.casefold() not in {"listening", "off", "sleeping"}:
			self._speakEcho(value)
		return True

	def _requestWSRPanelEvents(self):
		now = time.monotonic()
		if (
			self._wsrRequestedPid is None
			and now - self._lastWSRRequestTime < WSR_EVENT_REQUEST_RETRY_SECONDS
		):
			return
		self._lastWSRRequestTime = now
		try:
			windowHandle = winUser.FindWindow("MS:SpeechTopLevel", None)
			processId, _threadId = winUser.getWindowThreadProcessID(windowHandle)
			if not processId or processId == self._wsrRequestedPid:
				return
			eventHandler.requestEvents(
				eventName="show",
				processId=processId,
				windowClassName="#32770",
			)
			self._wsrRequestedPid = processId
			log.info(
				"DictationBridge Lite: requested legacy WSR correction-panel events for process %s",
				processId,
			)
		except Exception:
			# WSR is not necessarily running when NVDA loads. Focus and editable
			# value-change events retry this request after it starts.
			self._wsrRequestedPid = None
			return

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if getattr(obj, "windowClassName", "") != "#32770":
			return
		name = (getattr(obj, "name", "") or "").casefold()
		if "alternates panel" in name:
			clsList.insert(0, WSRAlternatesPanel)
		elif "spelling panel" in name:
			clsList.insert(0, WSRSpellingPanel)

	@staticmethod
	def _findWSRPanel(obj):
		current = obj
		for _ in range(12):
			if GlobalPlugin._isWSRPanel(current):
				return current
			current = getattr(current, "parent", None)
			if current is None:
				break
		return None

	@staticmethod
	def _isWSRPanel(obj):
		"""Recognize a WSR panel even if its overlay was applied too late."""
		if isinstance(obj, (WSRAlternatesPanel, WSRSpellingPanel)):
			return True
		if getattr(obj, "windowClassName", "") != "#32770":
			return False
		name = (getattr(obj, "name", "") or "").casefold()
		return "alternates panel" in name or "spelling panel" in name

	@staticmethod
	def _cleanWSRItemName(name):
		name = (name or "").strip()
		if len(name) >= 2 and name[0] in "❶❷❸❹❺❻❼❽❾❿":
			return name[1:].lstrip()
		return name

	@staticmethod
	def _positionPrefix(obj):
		try:
			index = (getattr(obj, "positionInfo", None) or {}).get("indexInGroup")
			return f"{index} " if index else ""
		except Exception:
			return ""

	def _panelAnnouncement(self, panel):
		parts = []
		panelName = getattr(panel, "name", "") or ""
		if panelName:
			parts.append(panelName)
		try:
			descendants = list(getattr(panel, "recursiveDescendants", []) or [])
		except Exception:
			descendants = []
		for descendant in descendants:
			states = getattr(descendant, "states", set()) or set()
			if controlTypes.State.INVISIBLE in states:
				continue
			name = getattr(descendant, "name", "") or ""
			role = getattr(descendant, "role", None)
			if role == controlTypes.Role.STATICTEXT and name:
				parts.append(name)
			elif role == controlTypes.Role.LINK and name:
				parts.append(_("Or say {text}").format(text=name))
			elif role == controlTypes.Role.LISTITEM and name:
				cleaned = self._cleanWSRItemName(name)
				parts.append(f"{self._positionPrefix(descendant)}{cleaned}".strip())
		# On some systems the show event arrives before the child controls exist.
		# The dialog description still contains the operating instructions, so use
		# it as a fallback rather than announcing only "Alternates panel".
		if len(parts) == 1:
			description = (getattr(panel, "description", "") or "").strip()
			if description:
				parts.extend(line.strip() for line in description.splitlines() if line.strip())
		return ". ".join(part for part in parts if part)

	def _scheduleWSRPanelAnnouncement(self, panel, force=False):
		"""Wait until Windows has populated a newly shown or reused panel."""
		wx.CallLater(
			WSR_PANEL_REFRESH_DELAY_MS,
			self._announceWSRPanel,
			panel,
			force,
		)

	def _announceWSRPanel(self, panel, force=False):
		if not self._enabled:
			return
		key = self._objectKey(panel)
		now = time.monotonic()
		if (
			not force
			and key == self._lastWSRPanelKey
			and now - self._lastWSRPanelTime < WSR_PANEL_DEDUP_SECONDS
		):
			return
		self._lastWSRPanelKey = key
		self._lastWSRPanelTime = now
		announcement = self._panelAnnouncement(panel)
		if announcement:
			self._speakEcho(announcement)
			log.info("DictationBridge Lite: announced legacy WSR correction panel")
		else:
			log.warning("DictationBridge Lite: WSR correction panel had no readable content")

	def _announceWSRSelection(self, obj):
		if not self._enabled:
			return
		name = self._cleanWSRItemName(getattr(obj, "name", "") or "")
		if not name:
			return
		key = (self._objectKey(obj), name)
		now = time.monotonic()
		if (
			key == self._lastWSRSelectionKey
			and now - self._lastWSRSelectionTime < WSR_PANEL_DEDUP_SECONDS
		):
			return
		self._lastWSRSelectionKey = key
		self._lastWSRSelectionTime = now
		self._speakEcho(f"{self._positionPrefix(obj)}{name}".strip())

	def event_show(self, obj, nextHandler):
		if self._isWSRPanel(obj):
			self._wsrPanelObject = obj
			# Let NVDA and other add-ons finish processing the dialog before we
			# inspect its descendants. Consuming this event left some WSR focus
			# objects incompletely initialized for keyboard add-ons.
			nextHandler()
			self._scheduleWSRPanelAnnouncement(obj)
			log.info("DictationBridge Lite: legacy WSR correction panel shown; announcement scheduled")
			return
		nextHandler()

	def event_selection(self, obj, nextHandler):
		if (
			getattr(obj, "role", None) == controlTypes.Role.LISTITEM
			and self._findWSRPanel(obj) is not None
		):
			nextHandler()
			self._announceWSRSelection(obj)
			return
		nextHandler()

	def event_stateChange(self, obj, nextHandler):
		states = getattr(obj, "states", set()) or set()
		if (
			getattr(obj, "role", None) == controlTypes.Role.LISTITEM
			and controlTypes.State.SELECTED in states
			and self._findWSRPanel(obj) is not None
		):
			nextHandler()
			self._announceWSRSelection(obj)
			return
		nextHandler()

	def event_typedCharacter(self, obj, nextHandler, ch):
		# Legacy offline Windows Speech Recognition can expose dictated text to
		# NVDA only as synthetic typed-character events, even while the native TSF
		# observer is active. Keep this path available alongside the native backend;
		# the raw-key grace period below distinguishes it from physical typing.
		if not self._rawKeyHandlerRegistered or not self._enabled or not ch:
			nextHandler()
			return
		if time.monotonic() - self._lastPhysicalKeyTime < PHYSICAL_KEY_GRACE_SECONDS:
			nextHandler()
			return
		if getattr(obj, "windowClassName", "") == "ConsoleWindowClass":
			nextHandler()
			return
		if self._isDuplicateOfRecentNativeInsertion(ch):
			return
		self._rememberFallbackInsertion(ch)
		self._enqueueInsertion(-1, ch)

	@script(
		description=_("Toggle DictationBridge Lite text echo"),
		category=_("DictationBridge Lite"),
	)
	def script_toggleEcho(self, gesture):
		self._setEchoEnabled(not self._enabled)
		ui.message(_("DictationBridge Lite echo on") if self._enabled else _("DictationBridge Lite echo off"))

	def terminate(self):
		self._cancelFlushTimer()
		self._removeToolsMenu()
		if self._speechFilterRegistered and self._speechFilter is not None:
			try:
				self._speechFilter.unregister(self._filterOnlineDuplicateSpeech)
			except Exception:
				log.exception("DictationBridge Lite: unable to unregister online speech filter")
			self._speechFilter = None
			self._speechFilterRegistered = False
		if self._native is not None:
			try:
				self._native.DBL_Stop()
			except Exception:
				log.exception("DictationBridge Lite: native backend did not stop cleanly")
			self._native = None
			self._nativeActive = False
		if self._rawKeyHandlerRegistered:
			try:
				inputCore.decide_handleRawKey.unregister(self._observeRawKey)
			except Exception:
				log.exception("DictationBridge Lite: unable to unregister raw-key observer")
			self._rawKeyHandlerRegistered = False
		super().terminate()
