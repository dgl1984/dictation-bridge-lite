import builtins
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
		self.plugin._rawKeyHandlerRegistered = True
		self.plugin._lastPhysicalKeyTime = 0.0

	def test_pending_text_uses_delayed_now_priority(self):
		self.plugin._pendingStart = 4
		self.plugin._pendingText = "select all"

		self.plugin._flushPending()

		self.assertEqual([("select all", "now")], self.messages)
		self.assertEqual([], self.spokenDirectly)

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

	def test_wsr_correction_panel_is_read_on_show_with_tooltip_safe_delivery(self):
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

		self.plugin.event_show(panel, lambda: nextHandlerCalls.append(True))

		self.assertEqual(
			[("Alternates panel. Choose an alternative. 1 first choice. 2 second choice", "now")],
			self.messages,
		)
		self.assertEqual([], nextHandlerCalls)

	def test_wsr_panel_overlay_is_restored(self):
		classes = []
		obj = types.SimpleNamespace(
			windowClassName="#32770",
			name="Alternates panel",
		)

		self.plugin.chooseNVDAObjectOverlayClasses(obj, classes)

		self.assertEqual([self.module.WSRAlternatesPanel], classes)


if __name__ == "__main__":
	unittest.main()
