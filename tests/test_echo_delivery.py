import builtins
import ctypes
import importlib.util
import sys
import time
import types
import unittest
from pathlib import Path


PLUGIN_PATH = (
	Path(__file__).parents[1]
	/ "addon"
	/ "globalPlugins"
	/ "dictationBridgeLite"
	/ "__init__.py"
)


class _Log:
	def __getattr__(self, name):
		return lambda *args, **kwargs: None


class _BaseGlobalPlugin:
	def terminate(self):
		pass


class _NVDAObject:
	pass


class _EditableObject:
	def __init__(self, role, editableState, text="", windowHandle=100):
		self.role = role
		self.states = {editableState}
		self.text = text
		self.windowHandle = windowHandle
		self.event_childID = 0
		self.windowClassName = "Notepad"

	def makeTextInfo(self, position):
		return types.SimpleNamespace(text=self.text)


class EchoDeliveryTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.messages = []
		cls.spokenDirectly = []
		cls.requestedEvents = []
		cls.wsrWindowAvailable = False
		cls._originalTranslation = getattr(builtins, "_", None)
		cls._hadWinFunctionType = hasattr(ctypes, "WINFUNCTYPE")
		if not cls._hadWinFunctionType:
			ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE
		builtins._ = lambda text: text

		addonHandler = types.ModuleType("addonHandler")
		addonHandler.initTranslation = lambda: None
		api = types.ModuleType("api")
		cls.focusObject = object()
		api.getFocusObject = lambda: cls.focusObject
		braille = types.ModuleType("braille")
		braille.handler = types.SimpleNamespace(handleCaretMove=lambda obj: None)
		controlTypes = types.ModuleType("controlTypes")
		controlTypes.Role = types.SimpleNamespace(
			EDITABLETEXT="editableText",
			STATICTEXT="staticText",
			LINK="link",
			LISTITEM="listItem",
		)
		controlTypes.State = types.SimpleNamespace(
			EDITABLE="editable",
			PROTECTED="protected",
			INVISIBLE="invisible",
			SELECTED="selected",
		)
		eventHandler = types.ModuleType("eventHandler")
		eventHandler.requestEvents = lambda **kwargs: cls.requestedEvents.append(kwargs)
		inputCore = types.ModuleType("inputCore")
		inputCore.decide_handleRawKey = types.SimpleNamespace(
			register=lambda handler: None,
			unregister=lambda handler: None,
		)
		queueHandler = types.ModuleType("queueHandler")
		queueHandler.eventQueue = object()
		queueHandler.queueFunction = lambda queue, function, *args: function(*args)
		speech = types.ModuleType("speech")
		speech.Spri = types.SimpleNamespace(NOW="now")
		speech.speakText = cls.spokenDirectly.append
		textInfos = types.ModuleType("textInfos")
		textInfos.POSITION_ALL = "all"
		ui = types.ModuleType("ui")
		ui.delayedMessage = lambda text, speechPriority=None: cls.messages.append(
			(text, speechPriority),
		)
		wx = types.ModuleType("wx")
		wx.CallLater = lambda *args, **kwargs: None
		globalPluginHandler = types.ModuleType("globalPluginHandler")
		globalPluginHandler.GlobalPlugin = _BaseGlobalPlugin
		gui = types.ModuleType("gui")
		gui.mainFrame = types.SimpleNamespace(sysTrayIcon=None)
		logHandler = types.ModuleType("logHandler")
		logHandler.log = _Log()
		NVDAObjects = types.ModuleType("NVDAObjects")
		NVDAObjects.NVDAObject = _NVDAObject
		scriptHandler = types.ModuleType("scriptHandler")
		scriptHandler.script = lambda **kwargs: lambda function: function
		winUser = types.ModuleType("winUser")
		winUser.FindWindow = lambda className, windowName: (
			300
			if cls.wsrWindowAvailable
			else (_ for _ in ()).throw(OSError())
		)
		winUser.getWindowThreadProcessID = lambda windowHandle: (500, 600)

		cls._stubModuleNames = {
			"addonHandler": addonHandler,
			"api": api,
			"braille": braille,
			"controlTypes": controlTypes,
			"eventHandler": eventHandler,
			"inputCore": inputCore,
			"queueHandler": queueHandler,
			"speech": speech,
			"textInfos": textInfos,
			"ui": ui,
			"winUser": winUser,
			"wx": wx,
			"NVDAObjects": NVDAObjects,
			"globalPluginHandler": globalPluginHandler,
			"gui": gui,
			"logHandler": logHandler,
			"scriptHandler": scriptHandler,
		}
		cls._originalModules = {
			name: sys.modules.get(name)
			for name in cls._stubModuleNames
		}
		sys.modules.update(cls._stubModuleNames)

		spec = importlib.util.spec_from_file_location("dictationBridgeLite_test", PLUGIN_PATH)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		cls.module = module
		cls.pluginClass = module.GlobalPlugin
		cls.roles = controlTypes.Role
		cls.states = controlTypes.State

	@classmethod
	def tearDownClass(cls):
		for name, original in cls._originalModules.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
		if cls._originalTranslation is None:
			del builtins._
		else:
			builtins._ = cls._originalTranslation
		if not cls._hadWinFunctionType:
			del ctypes.WINFUNCTYPE

	def setUp(self):
		self.messages.clear()
		self.spokenDirectly.clear()
		self.requestedEvents.clear()
		type(self).focusObject = object()
		type(self).wsrWindowAvailable = False
		self.plugin = self.pluginClass.__new__(self.pluginClass)
		self.plugin._enabled = True
		self.plugin._pendingStart = None
		self.plugin._pendingText = ""
		self.plugin._flushTimer = None
		self.plugin._nativeActive = True
		self.plugin._nativeDedupText = ""
		self.plugin._nativeDedupTime = 0.0
		self.plugin._nativeDeletedDedupText = ""
		self.plugin._nativeDeletedDedupTime = 0.0
		self.plugin._fallbackDedupText = ""
		self.plugin._fallbackDedupTime = 0.0
		self.plugin._fallbackDeletedDedupText = ""
		self.plugin._fallbackDeletedDedupTime = 0.0
		self.plugin._textSnapshots = {}
		self.plugin._wsrRequestedPid = None
		self.plugin._lastWSRRequestTime = 0.0
		self.plugin._lastWSRPanelKey = None
		self.plugin._lastWSRPanelTime = 0.0
		self.plugin._lastWSRSelectionKey = None
		self.plugin._lastWSRSelectionTime = 0.0
		self.plugin._wsrPanelObject = None
		self.plugin._lastWSRFeedback = ""
		self.plugin._lastOnlineCompositionTime = 0.0
		self.plugin._onlineSpeechDedupUntil = 0.0
		self.plugin._recentOnlineSpeech = {}
		self.plugin._rawKeyHandlerRegistered = True
		self.plugin._lastPhysicalKeyTime = 0.0
		self.plugin._echoMenuItem = None

	def test_pending_text_uses_delayed_now_priority(self):
		self.plugin._pendingStart = 4
		self.plugin._pendingText = "select all"

		self.plugin._flushPending()

		self.assertEqual([("select all", "now")], self.messages)
		self.assertEqual([], self.spokenDirectly)

	def test_exact_online_speech_repeat_is_filtered_only_during_commit_window(self):
		self.plugin._onlineSpeechDedupUntil = time.monotonic() + 2.0
		sequence = ["final online phrase"]

		self.assertIs(sequence, self.plugin._filterOnlineDuplicateSpeech(sequence))
		self.assertEqual([], self.plugin._filterOnlineDuplicateSpeech(sequence))

	def test_online_composition_is_not_echoed_or_stored_as_document_snapshot(self):
		obj = _EditableObject(self.roles.EDITABLETEXT, self.states.EDITABLE)
		obj.name = "Composition"
		type(self).focusObject = obj
		compositionKey = self.plugin._objectKey(obj)
		self.plugin._textSnapshots[compositionKey] = ""
		self.plugin._wsrRequestedPid = 500
		obj.text = "partial online words"

		self.plugin.event_valueChange(obj, lambda: None)
		self.plugin._flushPending()

		self.assertEqual([], self.messages)
		self.assertEqual("partial online words", self.plugin._textSnapshots[compositionKey])
		self.assertEqual((100, 0, "onlineComposition"), compositionKey)

	def test_online_commit_is_left_to_nvda_instead_of_echoing_partial_writes(self):
		obj = _EditableObject(self.roles.EDITABLETEXT, self.states.EDITABLE)
		obj.name = "Text Editor"
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = "before "
		self.plugin._wsrRequestedPid = 500
		self.plugin._lastOnlineCompositionTime = time.monotonic()
		obj.text = "before finalized online phrase"

		self.plugin.event_valueChange(obj, lambda: None)
		self.plugin._flushPending()

		self.assertEqual([], self.messages)

	def test_offline_echo_resumes_after_online_composition_grace_period(self):
		obj = _EditableObject(self.roles.EDITABLETEXT, self.states.EDITABLE)
		obj.name = "Text Editor"
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = ""
		self.plugin._wsrRequestedPid = 500
		type(self).wsrWindowAvailable = True
		self.plugin._lastOnlineCompositionTime = (
			time.monotonic() - self.module.ONLINE_COMPOSITION_GRACE_SECONDS - 1.0
		)
		self.plugin._lastPhysicalKeyTime = time.monotonic() - 1.0
		obj.text = "offline again"

		self.plugin.event_valueChange(obj, lambda: None)
		self.plugin._flushPending()

		self.assertEqual([("offline again", "now")], self.messages)

	def test_online_hint_and_routine_state_name_changes_are_suppressed(self):
		nextHandlerCalls = []
		base = {
			"appModule": types.SimpleNamespace(appName="textinputhost"),
			"name": 'Tip: Say "Select all"',
			"UIAAutomationId": "DictationHintControl",
		}
		self.plugin.event_nameChange(
			types.SimpleNamespace(**base),
			lambda: nextHandlerCalls.append(True),
		)
		base.update(name="Listening...", UIAAutomationId="DictationStateErrorControl")
		self.plugin.event_nameChange(
			types.SimpleNamespace(**base),
			lambda: nextHandlerCalls.append(True),
		)

		self.assertEqual([], nextHandlerCalls)

	def test_online_genuine_error_name_change_is_preserved(self):
		nextHandlerCalls = []
		obj = types.SimpleNamespace(
			appModule=types.SimpleNamespace(appName="textinputhost"),
			name="Check your microphone",
			UIAAutomationId="DictationStateErrorControl",
		)

		self.plugin.event_nameChange(obj, lambda: nextHandlerCalls.append(True))

		self.assertEqual([True], nextHandlerCalls)

	def test_online_settings_menu_uses_verified_windows_uri(self):
		calls = []
		event = types.SimpleNamespace(Skip=lambda: calls.append("skip"))
		original = getattr(self.module.os, "startfile", None)
		self.module.os.startfile = lambda target: calls.append(target)
		try:
			self.plugin._onOpenOnlineSettings(event)
		finally:
			if original is None:
				del self.module.os.startfile
			else:
				self.module.os.startfile = original

		self.assertEqual(
			["skip", "ms-settings:privacy-speech"],
			calls,
		)

	def test_offline_settings_menu_uses_verified_control_panel_command(self):
		calls = []
		event = types.SimpleNamespace(Skip=lambda: calls.append("skip"))
		original = self.module.subprocess.Popen
		self.module.subprocess.Popen = lambda command: calls.append(tuple(command))
		try:
			self.plugin._onOpenOfflineSettings(event)
		finally:
			self.module.subprocess.Popen = original

		self.assertEqual(
			[
				"skip",
				("control", "/name", "Microsoft.SpeechRecognition"),
			],
			calls,
		)

	def test_echo_toggle_updates_menu_check_state(self):
		checks = []
		self.plugin._echoMenuItem = types.SimpleNamespace(Check=checks.append)
		self.plugin._pendingText = "pending dictation"

		self.plugin._setEchoEnabled(False)

		self.assertFalse(self.plugin._enabled)
		self.assertEqual("", self.plugin._pendingText)
		self.assertEqual([False], checks)

	def test_tools_submenu_is_created_and_removed_without_leaking_entry(self):
		class FakeItem:
			nextId = 1

			def __init__(self, label):
				self.Id = self.nextId
				type(self).nextId += 1
				self.label = label
				self.checked = None
				self.destroyed = False

			def Check(self, checked):
				self.checked = checked

			def Destroy(self):
				self.destroyed = True

		class FakeMenu:
			def __init__(self):
				self.items = []
				self.removed = []
				self.destroyed = False

			def Append(self, _itemId, label, _helpText, kind=None):
				item = FakeItem(label)
				self.items.append((item, kind))
				return item

			def AppendSeparator(self):
				self.items.append((None, "separator"))

			def AppendSubMenu(self, submenu, label, _helpText):
				item = FakeItem(label)
				self.items.append((item, submenu))
				return item

			def Remove(self, itemId):
				self.removed.append(itemId)

			def Destroy(self):
				self.destroyed = True

		class FakeTrayIcon:
			def __init__(self):
				self.toolsMenu = FakeMenu()
				self.bindings = []
				self.unbindings = []

			def Bind(self, eventType, handler, source):
				self.bindings.append((eventType, handler, source))

			def Unbind(self, eventType, handler=None, source=None):
				self.unbindings.append((eventType, handler, source))

		trayIcon = FakeTrayIcon()
		originalMainFrame = self.module.gui.mainFrame
		originalMenu = getattr(self.module.wx, "Menu", None)
		originalIdAny = getattr(self.module.wx, "ID_ANY", None)
		originalItemCheck = getattr(self.module.wx, "ITEM_CHECK", None)
		originalEvtMenu = getattr(self.module.wx, "EVT_MENU", None)
		self.module.gui.mainFrame = types.SimpleNamespace(sysTrayIcon=trayIcon)
		self.module.wx.Menu = FakeMenu
		self.module.wx.ID_ANY = -1
		self.module.wx.ITEM_CHECK = "check"
		self.module.wx.EVT_MENU = "menu"
		for name in (
			"_toolsSubmenu",
			"_toolsMenuEntry",
			"_onlineSettingsMenuItem",
			"_offlineSettingsMenuItem",
			"_echoMenuItem",
		):
			setattr(self.plugin, name, None)
		try:
			self.plugin._createToolsMenu()
			entryId = self.plugin._toolsMenuEntry.Id
			labels = [item.label for item, _kind in self.plugin._toolsSubmenu.items if item]
			self.assertEqual(
				[
					"&Online dictation settings...",
					"O&ffline Speech Recognition settings...",
					"&Speak dictated text",
				],
				labels,
			)
			self.assertTrue(self.plugin._echoMenuItem.checked)
			self.assertEqual(3, len(trayIcon.bindings))

			self.plugin._removeToolsMenu()

			self.assertEqual([entryId], trayIcon.toolsMenu.removed)
			self.assertEqual(3, len(trayIcon.unbindings))
			self.assertIsNone(self.plugin._toolsSubmenu)
		finally:
			self.module.gui.mainFrame = originalMainFrame
			for name, original in (
				("Menu", originalMenu),
				("ID_ANY", originalIdAny),
				("ITEM_CHECK", originalItemCheck),
				("EVT_MENU", originalEvtMenu),
			):
				if original is None:
					delattr(self.module.wx, name)
				else:
					setattr(self.module.wx, name, original)

	def test_line_break_and_deletion_announcements_use_same_delivery_path(self):
		self.plugin._pendingStart = 0
		self.plugin._pendingText = "first\r\n\r\nsecond"

		self.plugin._announceDeletion("old\r\ntext")

		self.assertEqual(
			[
				("first", "now"),
				("new paragraph", "now"),
				("second", "now"),
				("deleted old text", "now"),
			],
			self.messages,
		)
		self.assertEqual([], self.spokenDirectly)

	def test_offline_wsr_typed_character_echo_remains_active_with_native_backend(self):
		nextHandlerCalls = []
		obj = types.SimpleNamespace(windowClassName="Notepad")

		self.plugin.event_typedCharacter(obj, lambda: nextHandlerCalls.append(True), "offline dictation")
		self.plugin._flushPending()

		self.assertEqual([("offline dictation", "now")], self.messages)
		self.assertEqual([], nextHandlerCalls)

	def test_native_and_typed_character_reports_are_not_echoed_twice(self):
		obj = types.SimpleNamespace(windowClassName="Notepad")

		self.plugin._nativeTextInserted(1, 0, "online")
		for ch in "online":
			self.plugin.event_typedCharacter(obj, lambda: None, ch)
		self.plugin._flushPending()

		self.assertEqual([("online", "now")], self.messages)
		self.assertEqual("", self.plugin._nativeDedupText)

	def test_physical_typing_is_not_captured_by_typed_character_fallback(self):
		nextHandlerCalls = []
		obj = types.SimpleNamespace(windowClassName="Notepad")
		self.plugin._lastPhysicalKeyTime = time.monotonic()

		self.plugin.event_typedCharacter(obj, lambda: nextHandlerCalls.append(True), "x")

		self.assertEqual([], self.messages)
		self.assertEqual([True], nextHandlerCalls)
		self.assertEqual("", self.plugin._pendingText)

	def test_offline_wsr_value_change_echoes_inserted_text(self):
		nextHandlerCalls = []
		obj = _EditableObject(self.roles.EDITABLETEXT, self.states.EDITABLE)
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = ""
		self.plugin._wsrRequestedPid = 500
		type(self).wsrWindowAvailable = True
		obj.text = "offline dictation"

		self.plugin.event_valueChange(obj, lambda: nextHandlerCalls.append(True))
		self.plugin._flushPending()

		self.assertEqual([("offline dictation", "now")], self.messages)
		self.assertEqual([True], nextHandlerCalls)

	def test_physical_typing_is_not_captured_by_value_change_fallback(self):
		nextHandlerCalls = []
		obj = _EditableObject(self.roles.EDITABLETEXT, self.states.EDITABLE)
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = ""
		self.plugin._wsrRequestedPid = 500
		type(self).wsrWindowAvailable = True
		self.plugin._lastPhysicalKeyTime = time.monotonic()
		obj.text = "x"

		self.plugin.event_valueChange(obj, lambda: nextHandlerCalls.append(True))
		self.plugin._flushPending()

		self.assertEqual([], self.messages)
		self.assertEqual([True], nextHandlerCalls)
		self.assertEqual("x", self.plugin._textSnapshots[self.plugin._objectKey(obj)])

	def test_native_then_value_change_is_not_echoed_twice(self):
		obj = _EditableObject(self.roles.EDITABLETEXT, self.states.EDITABLE)
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = ""
		self.plugin._wsrRequestedPid = 500
		type(self).wsrWindowAvailable = True

		self.plugin._nativeTextInserted(100, 0, "online")
		obj.text = "online"
		self.plugin.event_valueChange(obj, lambda: None)
		self.plugin._flushPending()

		self.assertEqual([("online", "now")], self.messages)

	def test_value_change_then_native_is_not_echoed_twice(self):
		obj = _EditableObject(self.roles.EDITABLETEXT, self.states.EDITABLE)
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = ""
		self.plugin._wsrRequestedPid = 500
		type(self).wsrWindowAvailable = True

		obj.text = "online"
		self.plugin.event_valueChange(obj, lambda: None)
		self.plugin._nativeTextInserted(100, 0, "online")
		self.plugin._flushPending()

		self.assertEqual([("online", "now")], self.messages)

	def test_native_then_value_change_deletion_is_not_echoed_twice(self):
		obj = _EditableObject(
			self.roles.EDITABLETEXT,
			self.states.EDITABLE,
			text="old text",
		)
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = "old text"
		self.plugin._wsrRequestedPid = 500
		type(self).wsrWindowAvailable = True

		self.plugin._nativeTextDeleted(100, 0, "old text")
		obj.text = ""
		self.plugin.event_valueChange(obj, lambda: None)

		self.assertEqual([("deleted old text", "now")], self.messages)

	def test_value_change_then_native_deletion_is_not_echoed_twice(self):
		obj = _EditableObject(
			self.roles.EDITABLETEXT,
			self.states.EDITABLE,
			text="old text",
		)
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = "old text"
		self.plugin._wsrRequestedPid = 500
		type(self).wsrWindowAvailable = True

		obj.text = ""
		self.plugin.event_valueChange(obj, lambda: None)
		self.plugin._nativeTextDeleted(100, 0, "old text")

		self.assertEqual([("deleted old text", "now")], self.messages)

	def test_value_change_fallback_is_inactive_when_legacy_wsr_is_not_running(self):
		obj = _EditableObject(self.roles.EDITABLETEXT, self.states.EDITABLE)
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = ""
		obj.text = "pasted with the mouse"

		self.plugin.event_valueChange(obj, lambda: None)
		self.plugin._flushPending()

		self.assertEqual([], self.messages)

	def test_offline_wsr_uia_text_change_uses_the_same_fallback(self):
		obj = _EditableObject(self.roles.EDITABLETEXT, self.states.EDITABLE)
		type(self).focusObject = obj
		self.plugin._textSnapshots[self.plugin._objectKey(obj)] = ""
		self.plugin._wsrRequestedPid = 500
		type(self).wsrWindowAvailable = True
		obj.text = "UIA offline dictation"

		self.plugin.event_textChange(obj, lambda: None)
		self.plugin._flushPending()

		self.assertEqual([("UIA offline dictation", "now")], self.messages)

	def test_wsr_correction_panel_is_read_after_show_event_finishes(self):
		panel = self.module.WSRAlternatesPanel()
		panel.name = "Alternates panel"
		panel.windowHandle = 200
		panel.event_childID = 0
		panel.recursiveDescendants = [
			types.SimpleNamespace(
				role=self.roles.STATICTEXT,
				states=set(),
				name="Choose an alternative",
			),
			types.SimpleNamespace(
				role=self.roles.LISTITEM,
				states=set(),
				name="❶ first choice",
				positionInfo={"indexInGroup": 1},
			),
			types.SimpleNamespace(
				role=self.roles.LISTITEM,
				states=set(),
				name="❷ second choice",
				positionInfo={"indexInGroup": 2},
			),
		]
		nextHandlerCalls = []
		calls = []
		originalCallLater = self.module.wx.CallLater
		self.module.wx.CallLater = lambda delay, function, *args: calls.append(
			(delay, function, args)
		)
		try:
			self.plugin.event_show(panel, lambda: nextHandlerCalls.append(True))
		finally:
			self.module.wx.CallLater = originalCallLater

		self.assertEqual([True], nextHandlerCalls)
		self.assertEqual(1, len(calls))
		self.assertEqual(self.module.WSR_PANEL_REFRESH_DELAY_MS, calls[0][0])
		calls[0][1](*calls[0][2])

		self.assertEqual(
			[("Alternates panel. Choose an alternative. 1 first choice. 2 second choice", "now")],
			self.messages,
		)

	def test_wsr_panel_without_overlay_is_still_recognized(self):
		panel = types.SimpleNamespace(
			windowClassName="#32770",
			name="Alternates panel",
			description="Say the number next to the item you want, followed by OK",
			recursiveDescendants=[],
			windowHandle=200,
			event_childID=0,
		)

		self.assertTrue(self.plugin._isWSRPanel(panel))
		self.assertEqual(panel, self.plugin._findWSRPanel(panel))
		self.assertEqual(
			"Alternates panel. Say the number next to the item you want, followed by OK",
			self.plugin._panelAnnouncement(panel),
		)

	def test_wsr_selection_is_announced_without_consuming_nvda_event(self):
		panel = self.module.WSRAlternatesPanel()
		item = types.SimpleNamespace(
			role=self.roles.LISTITEM,
			name="❶ first choice",
			positionInfo={"indexInGroup": 1},
			parent=panel,
			windowHandle=201,
			event_childID=1,
		)
		nextHandlerCalls = []

		self.plugin.event_selection(item, lambda: nextHandlerCalls.append(True))

		self.assertEqual([True], nextHandlerCalls)
		self.assertEqual([("1 first choice", "now")], self.messages)

	def test_wsr_panel_overlay_is_restored(self):
		classes = []
		obj = types.SimpleNamespace(
			windowClassName="#32770",
			name="Alternates panel",
		)

		self.plugin.chooseNVDAObjectOverlayClasses(obj, classes)

		self.assertEqual([self.module.WSRAlternatesPanel], classes)

	def test_actionable_wsr_feedback_is_announced(self):
		nextHandlerCalls = []
		self.plugin._wsrRequestedPid = 500
		obj = types.SimpleNamespace(
			processID=500,
			windowClassName="MS:SpeechTopLevel",
			name="Speech Recognition feedback",
			value="You must select an item.",
		)

		self.plugin.event_valueChange(obj, lambda: nextHandlerCalls.append(True))

		self.assertEqual([("You must select an item.", "now")], self.messages)
		self.assertEqual([True], nextHandlerCalls)

	def test_reused_wsr_panel_is_scheduled_for_forced_refresh(self):
		calls = []
		panel = self.module.WSRAlternatesPanel()
		self.plugin._wsrRequestedPid = 500
		self.plugin._wsrPanelObject = panel
		obj = types.SimpleNamespace(
			processID=500,
			windowClassName="MS:SpeechTopLevel",
			name="Speech Recognition feedback",
			value="Correcting mistaken words",
		)
		originalCallLater = self.module.wx.CallLater
		self.module.wx.CallLater = lambda delay, function, *args: calls.append(
			(delay, function, args)
		)
		try:
			self.assertTrue(self.plugin._handleWSRFeedback(obj))
		finally:
			self.module.wx.CallLater = originalCallLater

		self.assertEqual(1, len(calls))
		self.assertEqual(self.module.WSR_PANEL_REFRESH_DELAY_MS, calls[0][0])
		self.assertEqual((panel, True), calls[0][2])


if __name__ == "__main__":
	unittest.main()
