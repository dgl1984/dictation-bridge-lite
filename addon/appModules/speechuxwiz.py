# Copyright (C) 2016-2020 DictationBridge contributors
# Copyright (C) 2026 Derek Lane and DictationBridge Lite contributors
# SPDX-License-Identifier: GPL-2.0-only

"""Accessibility support for the Windows Speech Recognition training wizard.

This is a focused modernization of DictationBridge's original speechuxwiz app
module.  It intentionally restores the useful training-prompt announcements
without restoring WSR macros, screen-reader voice commands, or Dragon support.
"""

import api
import appModuleHandler
import controlTypes
import queueHandler
import ui
from NVDAObjects.UIA import UIA
from NVDAObjects.behaviors import Dialog


class Wizard(Dialog):
	role = controlTypes.Role.DIALOG


class AppModule(appModuleHandler.AppModule):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._lastTrainingText = ""

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if obj.windowClassName == "NativeHWNDHost" and obj.role == controlTypes.Role.PANE:
			clsList.insert(0, Wizard)

	def event_NVDAObject_init(self, obj):
		# The headset-microphone radio button can create a spurious UIA focus
		# event after it has been selected for a moment.
		if (
			isinstance(obj, UIA)
			and obj.role == controlTypes.Role.WINDOW
			and obj.UIAElement.cachedClassName == "CCRadioButton"
		):
			obj.shouldAllowUIAFocusEvent = False
		if obj.role == controlTypes.Role.STATICTEXT and obj.description:
			obj.description = None

	def _announceTrainingText(self, force=False):
		window = api.getForegroundObject()
		if window is None:
			return
		for descendant in window.recursiveDescendants:
			if not isinstance(descendant, UIA):
				continue
			try:
				isTrainingText = descendant.UIAAutomationId == "txttrain"
			except Exception:
				continue
			if not isTrainingText:
				continue
			text = descendant.name or ""
			if text and (force or text != self._lastTrainingText):
				self._lastTrainingText = text
				api.setNavigatorObject(descendant)
				ui.message(text)
			return

	def script_readTrainingText(self, gesture):
		"""Read the current training passage again."""
		self._announceTrainingText(force=True)

	__gestures = {
		"kb:`": "readTrainingText",
	}

	def event_foreground(self, obj, nextHandler):
		nextHandler()
		# Defer the scan until NVDA has finished constructing the foreground
		# object's UIA descendants.
		queueHandler.queueFunction(queueHandler.eventQueue, self._announceTrainingText)

	def event_nameChange(self, obj, nextHandler):
		if (
			obj.role == controlTypes.Role.STATICTEXT
			and obj.windowClassName == "DirectUIHWND"
		):
			self._announceTrainingText()
		nextHandler()

	def event_valueChange(self, obj, nextHandler):
		if obj.role == controlTypes.Role.PROGRESSBAR:
			self._announceTrainingText()
		nextHandler()
