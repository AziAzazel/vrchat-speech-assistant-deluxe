"""Roleplay controls and editable announcement shortcuts."""
from PySide6 import QtWidgets, QtGui
from vrchat_speech_assistant.shortcut_editor import ShortcutEdit, HotkeySettingsDialog
from vrchat_speech_assistant.roleplay import PERSONALITIES, DELIVERIES, ACTIONS, DEFAULT_HOTKEYS
from vrchat_speech_assistant.hotkeys import parse_hotkey
from vrchat_speech_assistant.languages import GOOGLE, DEEPL


class RoleplayDialog(HotkeySettingsDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Personality, delivery and hotkeys")
        self.resize(720, 500)
        self.window = parent
        settings = parent.config["ROLEPLAY"]
        layout = QtWidgets.QVBoxLayout(self)
        self.personality = QtWidgets.QComboBox()
        self.personality.addItems(PERSONALITIES)
        self.personality.setCurrentText(settings["personality"])
        self.delivery = QtWidgets.QComboBox()
        self.delivery.addItems(DELIVERIES)
        self.delivery.setCurrentText(settings["delivery"])
        self.personality.currentTextChanged.connect(lambda name: self.delivery.setCurrentText(PERSONALITIES[name][0]))
        layout.addWidget(QtWidgets.QLabel("Personality (announcement lines and optional chatbox tag):"))
        layout.addWidget(self.personality)
        layout.addWidget(QtWidgets.QLabel("Delivery (all speech); genuine whisper requires Polly:"))
        layout.addWidget(self.delivery)
        self.tag = QtWidgets.QCheckBox("Add personality tag to chatbox output")
        self.tag.setChecked(settings.getboolean("chatbox_tag"))
        layout.addWidget(self.tag)
        self.global_keys = QtWidgets.QCheckBox("Enable global Windows hotkeys while VRChat is focused")
        self.global_keys.setChecked(settings.getboolean("global_hotkeys"))
        self.global_keys.setEnabled(parent.global_shortcuts_checkbox.isEnabled())
        layout.addWidget(self.global_keys)
        layout.addWidget(QtWidgets.QLabel("With global keys off, shortcuts work only while this app is focused. Clear a key to disable it."))
        self.language_first = QtWidgets.QComboBox()
        self.language_second = QtWidgets.QComboBox()
        for combo, field in ((self.language_first, "first"), (self.language_second, "second")):
            combo.addItems([name for name in GOOGLE if name in DEEPL])
            combo.setCurrentText(parent.config["LANGUAGES"].get(field))
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Language hotkey pair (recognition and output):"))
        row.addWidget(self.language_first)
        row.addWidget(self.language_second)
        layout.addLayout(row)
        self.table = QtWidgets.QTableWidget(len(ACTIONS), 3)
        self.table.setHorizontalHeaderLabels(["Action", "Hotkey", "Custom announcement (blank = personality default)"])
        for row, action in enumerate(ACTIONS):
            self.table.setCellWidget(row, 0, QtWidgets.QLabel(action.replace("_", " ")))
            key = ShortcutEdit(QtGui.QKeySequence(settings.get("key_" + action, DEFAULT_HOTKEYS[action])))
            self.table.setCellWidget(row, 1, key)
            phrase = QtWidgets.QLineEdit(settings.get("phrase_" + action, ""))
            phrase.setEnabled(action in ACTIONS[:4])
            self.table.setCellWidget(row, 2, phrase)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        bindings = {}
        seen = {parse_hotkey(preset['key']) for preset in self.window.soundboard_presets if preset['key']}
        try:
            for row, action in enumerate(ACTIONS):
                sequence = self.table.cellWidget(row, 1).keySequence().toString(QtGui.QKeySequence.PortableText)
                if sequence:
                    canonical = parse_hotkey(sequence)
                    if canonical in seen:
                        raise ValueError("Each action must have a different hotkey")
                    seen.add(canonical)
                bindings[action] = sequence
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, "Invalid hotkeys", str(error))
            return
        settings = self.window.config["ROLEPLAY"]
        settings.update(personality=self.personality.currentText(), delivery=self.delivery.currentText(),
                        chatbox_tag=str(self.tag.isChecked()), global_hotkeys=str(self.global_keys.isChecked()))
        for row, action in enumerate(ACTIONS):
            settings["key_" + action] = bindings[action]
            settings["phrase_" + action] = self.table.cellWidget(row, 2).text()
        self.window.config["LANGUAGES"]["first"] = self.language_first.currentText()
        self.window.config["LANGUAGES"]["second"] = self.language_second.currentText()
        self.window.save_config()
        self.window._init_hotkeys()
        self.accept()
