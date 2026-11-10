"""The VRChat Speech Assistant allows you to easily use a speech to speech, with automatic translation.

And / or speech to text with the VRChat chatbox using OSC protocol. """

import configparser
import json
import logging
import threading
import time
from datetime import datetime
import contextlib
import sys
import webbrowser
import winsound
from os import getenv
from pathlib import Path
from threading import Thread

import speech_recognition
from chatbox_osc import FONTS, write_chatbox
from vrchat_speech_assistant.audio_devices import get_devices
from vrchat_speech_assistant.listener import BackgroundListener
from vrchat_speech_assistant.output_control import output_scope, check_cancelled, OutputCancelled, CancellableOSC
from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal, QTimer
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from vrchat_speech_assistant import darkstyle, icons
from vrchat_speech_assistant.languages import DEEPL, GOOGLE, VOICES
from vrchat_speech_assistant.providers import Polly
from vrchat_speech_assistant.windows_speech import (
    WindowsSpeech, UnavailableWindowsSpeech, SpeechWithFallback,
)
from vrchat_speech_assistant.utils import test_deepl
from vrchat_speech_assistant.widgets import ConfigDialog
try:
    from vrchat_speech_assistant import _config
except ImportError:
    from vrchat_speech_assistant import provider_defaults as _config


from vrchat_speech_assistant.diagnostics import DATA_DIR, record_failure
from vrchat_speech_assistant.text_tools import correct_nicknames, decorate_chatbox, add_random_ending
from vrchat_speech_assistant.piper_speech import PiperSpeech
from vrchat_speech_assistant.roleplay import PERSONALITIES, DELIVERIES, ACTIONS, DEFAULT_HOTKEYS, announcement, spoken_delivery
from vrchat_speech_assistant.hotkeys import GlobalHotkeys, parse_hotkey
from vrchat_speech_assistant.responsive_ui import ResponsiveCards, CollapsibleCard

CONFIG_FILE = DATA_DIR / "config.ini"
RESOURCES_PATH = Path(__file__).parent / "resources"

logger = logging.getLogger("deluxe.main")
dispatcher = Dispatcher()


class VRCSpeechAssistantWindow(QtWidgets.QWidget):
    """The main window of the VRC Speech Assistant application.

    Using the parameters chosen by the user, this application allows you to use a
    speech to speech, or speech to text, or both, with your chosen provider.
    You can also use a translator to auto translate your sentence using DeepL.

    Note
    ----
        - The recognizer uses Google services, no configuration needed.
        - Amazon Polly need an API key, but a default one is provided.
        - DeepL translator need an API key, but a default one is provided.

    Attributes
    ----------
    DEFAULT_WIDTH: int
        The default window width.
    DEFAULT_HEIGHT: int
        The default window height.
    SPEECH_GROUPBOX_HEIGHT: int
        The speech groupbox widget height size.
    CHATBOX_GROUPBOX_HEIGHT: int
        The chatbox groupbox widget height size.
    CONFIG: dict
        The default configuration dictionary for the application.
    speech_provider: object
        The selected speech provider for the speech engine.
    extra_tags: dict
        Optional extra tags to be provided to the speech provider object.
    osc_client: SimpleUDPClient
        The OSC client for VRChat on port 9000.
    osc_server: BlockingOSCUDPServer
        The OSC server that allows the user to interact with the app trough OSC
        on port 7001.
    listener: speech_recognition.Recognizer.listen_in_background
        The listener object when the listener thread is running.
    is_listener_running: bool
        The state of the listener thread.
    input_devices: list
        A list of input sounddevice dict.
    output_devices: list
        A list of input sounddevice dict.
    config: configparser.ConfigParser
        The configuration file parser.
    """

    status_signal = Signal(str, str)
    activity_signal = Signal(bool)
    hotkey_state_signal = Signal(str)
    history_entry_signal = Signal(object)
    history_changed = Signal()
    recognized_signal = Signal(str, int)
    devices_signal = Signal(object, object)
    capture_failed_signal = Signal(object, object)
    output_failed_signal = Signal()
    finished_signal = Signal()
    command_signal = Signal(object)

    DEFAULT_WIDTH = 420
    DEFAULT_HEIGHT = 850
    SPEECH_GROUPBOX_HEIGHT = 390
    CHATBOX_GROUPBOX_HEIGHT = 140
    CONFIG = {
        "APP": {
            "beep": True,
            "input_device": None,
        },
        "UI": {"width": 1000, "height": 800, "maximized": False},
        "ENDING": {"text": "", "frequency": 0},
        "PREVIEW": {"enabled": True, "delay": 3.0},
        "LANGUAGES": {"first": "English", "second": "Polish"},
        "API": {
            "deepl_api_key": "",
            "aws_access_key": "",
            "aws_secret_key": "",
            "aws_region": "us-west-2",
        },
        "TRANSLATOR": {
            "split_sentences": 1,
            "formality": "Default",
        },
        "SPEECH": {
            "enabled": True,
            "show more settings": False,
            "source_language": "English",
            "target_language": "English",
            "provider": "Windows Speech",
            "polly_fallback": False,
            "fallback_voice": "Justin",
            "piper_model": "",
            "piper_executable": "",
            "voice": "Justin",
            "pitch": 0,
            "output_device": None,
        },
        "ROLEPLAY": {
            "personality": "Neutral", "delivery": "Normal",
            "chatbox_tag": False, "global_hotkeys": True,
            "global_scope_migrated": False,
            **{"key_" + action: key for action, key in DEFAULT_HOTKEYS.items()},
        },
        "CHATBOX": {
            "enabled": True,
            "show more settings": False,
            "font": "Normal",
            "animation": True,
            "keyword_additions": False,
        },
    }

    def __init__(self):
        super().__init__()
        self.status_signal.connect(self._show_status)
        self.activity_signal.connect(self._voice_activity)
        self.recognized_signal.connect(self._submit_recognized)
        self.finished_signal.connect(self._finish_output)
        self.command_signal.connect(lambda command: command())
        self.devices_signal.connect(self._apply_devices)
        self.capture_failed_signal.connect(self._capture_failed)
        self.output_failed_signal.connect(self.refresh_devices)
        self.cancel_output = threading.Event()
        self.recognition_epoch = 0
        self.listener_session = None
        self.recover_listener = False
        self.capture_retry_after = 0
        self.device_scan_busy = False
        self.pending_draft = False
        self.editor_dirty = False
        self.loading_editor = False
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.speak_manual_text)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._update_countdown)
        self.ui_ready = False
        self.voice_scope = None
        self.geometry_timer = QTimer(self)
        self.geometry_timer.setSingleShot(True)
        self.geometry_timer.timeout.connect(self._save_window_size)
        self.history = []
        self.history_sequence = 0
        self.history_entry_signal.connect(self._record_history)
        self.output_busy = False
        self.windows_speech = None
        self._closing = False
        self.translator = None
        self.speech_provider = None
        self.extra_tags = {}
        self.osc_client = SimpleUDPClient("127.0.0.1", 9000)
        self.osc_server = BlockingOSCUDPServer(("127.0.0.1", 7001), dispatcher)
        self.listener = None
        self.is_listener_running = False
        self.input_devices = self._detect_devices("input")
        self.output_devices = self._detect_devices("output")
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=None)
        self._init_config()
        self._init_ui()
        self._init_translator()
        self._init_server()
        self.global_hotkeys = None
        self.shortcuts = []
        self._init_hotkeys()
        self.device_timer = QTimer(self)
        self.device_timer.timeout.connect(self.refresh_devices)
        self.device_timer.start(5000)
        self.ui_ready = True
        if self.config["UI"].getboolean("maximized"):
            self.setWindowState(self.windowState() | Qt.WindowMaximized)

    @staticmethod
    def _detect_devices(kind):
        try:
            return get_devices(device_type=kind)
        except Exception:
            # A headless runner or disconnected audio API can expose no devices.
            record_failure("Enumerate " + kind + " devices", *sys.exc_info()[::2])
            return []

    def _init_config(self):
        self._load_base_config()
        if CONFIG_FILE.exists():
            self.config.read(CONFIG_FILE, encoding="utf8")
        if not self.config["ROLEPLAY"].getboolean("global_scope_migrated"):
            self.config["ROLEPLAY"]["global_hotkeys"] = "True"
            self.config["ROLEPLAY"]["global_scope_migrated"] = "True"
            for action, previous in (("speak_paste", "Ctrl+Alt+F12"), ("switch_language", "Ctrl+Shift+F12")):
                if self.config["ROLEPLAY"].get("key_" + action) == previous:
                    self.config["ROLEPLAY"]["key_" + action] = DEFAULT_HOTKEYS[action]
        self.pronunciations = {}
        try:
            path = DATA_DIR / "pronunciation.json"
            if path.exists():
                rules = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(rules, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in rules.items()):
                    raise ValueError("Invalid pronunciation dictionary")
                self.pronunciations = rules
        except (ValueError, OSError):
            record_failure("Load pronunciation dictionary", *sys.exc_info()[::2])
        self.chatbox_rules = {}
        try:
            path = DATA_DIR / "chatbox-rules.json"
            if path.exists():
                rules = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(rules, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in rules.items()):
                    raise ValueError("Invalid keyword additions")
                self.chatbox_rules = rules
        except (ValueError, OSError):
            record_failure("Load chatbox additions", *sys.exc_info()[::2])
        self.corrections = {}
        correction_file = DATA_DIR / "nicknames.json"
        if correction_file.exists():
            try:
                self.corrections = json.loads(correction_file.read_text(encoding="utf-8"))
                if not isinstance(self.corrections, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in self.corrections.items()
                ):
                    raise ValueError("Invalid nickname dictionary")
            except (ValueError, OSError):
                self.corrections = {}
                record_failure("Load nickname dictionary", *sys.exc_info()[::2])
        self.save_config()

    def _load_base_config(self):
        for section, options in self.CONFIG.items():
            self.config[section] = options
        if self.input_devices:
            self.config["APP"]["input_device"] = self.input_devices[0]["name"]
        if self.output_devices:
            self.config["SPEECH"]["output_device"] = self.output_devices[0]["name"]

    def _init_ui(self):
        self.setWindowFlag(Qt.Window)
        self.setWindowTitle("VRChat Speech Assistant")
        self.setWindowIcon(QtGui.QIcon(str(RESOURCES_PATH / "logo.png")))
        self.setMinimumSize(420, 400)
        screen = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        width = min(screen.width(), max(420, self.config["UI"].getint("width")))
        height = min(screen.height(), max(400, self.config["UI"].getint("height")))
        self.resize(width, height)
        ######### Menubar #########
        menu_bar = QtWidgets.QMenuBar(self)
        file_menu = menu_bar.addMenu("File")
        file_open_config_folder = file_menu.addAction("Open config folder", self.open_config_folder)
        file_open_config_folder.setIcon(QtGui.QIcon(str(RESOURCES_PATH / "folder.png")))
        file_menu.addAction("Open diagnostic logs", self.open_logs)
        file_menu.addAction("Session history", self.show_history)
        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction("Nickname corrections", self.edit_nicknames)
        edit_menu.addAction("Pronunciation dictionary (speech only)", self.edit_pronunciations)
        edit_menu.addAction("Chatbox keyword additions", self.edit_chatbox_rules)
        edit_configuration_action = edit_menu.addAction("Configuration", self.edit_config)
        edit_configuration_action.setIcon(QtGui.QIcon(str(RESOURCES_PATH / "edit.png")))
        roleplay_menu = menu_bar.addMenu("Roleplay")
        roleplay_menu.addAction("Personality, delivery and hotkeys", self.edit_roleplay)
        for action in ACTIONS[:4]:
            roleplay_menu.addAction(action.title(), lambda checked=False, name=action: self.roleplay_action(name))
        more_menu = menu_bar.addMenu("More")
        open_web_action = more_menu.addAction("Open Deluxe Repository", self.open_repository)
        open_web_action.setIcon(QtGui.QIcon(str(RESOURCES_PATH / "web.png")))
        ######### Main layout #########
        container = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(container)
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        ######### Banner #########
        banner = QtWidgets.QLabel(self)
        banner.setPixmap(QtGui.QPixmap(str(RESOURCES_PATH / "banner.png")).scaledToHeight(52, Qt.SmoothTransformation))
        banner.setAlignment(Qt.AlignCenter)
        tips_label = QtWidgets.QLabel("Speak clearly and avoid any source of background noise.")
        ######### Speech input widget #########
        input_device_label = QtWidgets.QLabel("Input device:")
        self.input_device_combo = QtWidgets.QComboBox()
        input_device_names = [item["name"] for item in self.input_devices]
        self.input_device_combo.addItems(input_device_names)
        saved_input_device = self.config["APP"].get("input_device")
        if saved_input_device and saved_input_device in input_device_names:
            self.input_device_combo.setCurrentText(saved_input_device)
        self.input_device_combo.currentTextChanged.connect(self._on_input_device_clicked)
        ############ Source language widget #########
        source_language_label = QtWidgets.QLabel("Source language:")
        self.source_language_combo = QtWidgets.QComboBox()
        self.source_language_combo.addItems(GOOGLE.keys())
        self.source_language_combo.setCurrentText(self.config["SPEECH"].get("source_language"))
        self.source_language_combo.currentTextChanged.connect(self._on_source_language_combo_clicked)
        ######### Target language widget #########
        target_language_label = QtWidgets.QLabel("Target language:")
        self.target_language_combo = QtWidgets.QComboBox()
        self.target_language_combo.addItems(DEEPL.keys())
        self.target_language_combo.setCurrentText(self.config["SPEECH"].get("target_language"))
        self.target_language_combo.currentTextChanged.connect(self._on_target_language_combo_clicked)
        ######### Formality widget #########
        formality_label = QtWidgets.QLabel("DeepL translation formality:")
        self.formality_combo = QtWidgets.QComboBox()
        self.formality_combo.addItems(["Default", "Formal", "Informal"])
        self.formality_combo.setCurrentText(self.config["TRANSLATOR"].get("formality"))
        self.formality_combo.currentTextChanged.connect(self._on_formality_combo_clicked)
        ######### Progressbar #########
        self.progressbar = QtWidgets.QProgressBar(self)
        self.progressbar.setStyleSheet("border-style: none")
        ######### Speech groupbox widget #########
        self.speech_status_checkbox = QtWidgets.QCheckBox("Speech")
        self.speech_status_checkbox.setChecked(self.config["SPEECH"].getboolean("enabled"))
        self.speech_status_checkbox.stateChanged.connect(self._on_speech_status_checkbox_clicked)
        self.speech_groupbox = QtWidgets.QGroupBox(self)
        self.speech_groupbox.setEnabled(self.config["SPEECH"].getboolean("enabled"))
        saved_speech_settings_shown = self.config["SPEECH"].getboolean("show more settings")
        self.speech_groupbox.setVisible(saved_speech_settings_shown)
        speech_groupbox_layout = QtWidgets.QVBoxLayout(self.speech_groupbox)
        ######### Speech provider widget #########
        speech_provider_label = QtWidgets.QLabel("Speech provider:")
        self.speech_provider_combo = QtWidgets.QComboBox()
        self.speech_provider_combo.addItems(["Windows Speech", "Piper (offline)", "Amazon Polly"])
        self.speech_provider_combo.setCurrentText(self.config["SPEECH"].get("provider"))
        self.speech_provider_combo.currentTextChanged.connect(self._on_speech_provider_combo_clicked)
        self.piper_model_button = QtWidgets.QPushButton("Choose Piper voice model (.onnx)")
        self.piper_model_button.clicked.connect(self.choose_piper_model)
        self.piper_backend_button = QtWidgets.QPushButton("Choose external Piper backend (piper.exe)")
        self.piper_backend_button.clicked.connect(self.choose_piper_backend)
        self.polly_fallback_checkbox = QtWidgets.QCheckBox("Use Polly if local synthesis fails (online; AWS charges)")
        self.polly_fallback_checkbox.setChecked(self.config["SPEECH"].getboolean("polly_fallback"))
        self.polly_fallback_checkbox.toggled.connect(self._on_fallback_changed)
        self.fallback_voice_combo = QtWidgets.QComboBox()
        self.fallback_voice_combo.currentTextChanged.connect(self._on_fallback_voice_changed)
        self.local_voice_note = QtWidgets.QLabel("Local voices use their natural style; whisper/pitch effects require Polly.")
        self.local_voice_note.setWordWrap(True)
        ######### Extra tags widgets #########
        extra_tags_label = QtWidgets.QLabel("Extra tags:")
        self.extra_tags_combo = QtWidgets.QComboBox()
        self.extra_tags_combo.addItems(["None", "Whispered"])
        self.extra_tags_combo.currentTextChanged.connect(self._on_extra_tags_combo_clicked)
        ######### Speech voices widget #########
        speech_voice_label = QtWidgets.QLabel("Voice:")
        self.speech_voice_combo = QtWidgets.QComboBox()
        ######### Speech pitch widget #########
        speech_pitch_label = QtWidgets.QLabel("Voice pitch:")
        self.speech_pitch_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.speech_pitch_slider.setRange(-50, 50)
        saved_pitch = max(-50, min(50, self.config["SPEECH"].getint("pitch")))
        self.speech_pitch_slider.setValue(saved_pitch)
        if saved_pitch:
            self.extra_tags["pitch"] = saved_pitch
        self.speech_pitch_slider.valueChanged.connect(self._on_speech_pitch_value_changed)
        ######### Speech output widget #########
        output_device_label = QtWidgets.QLabel("Output device:")
        self.output_device_combo = QtWidgets.QComboBox()
        output_device_names = [item["name"] for item in self.output_devices]
        self.output_device_combo.addItems(output_device_names)
        saved_output_device = self.config["SPEECH"].get("output_device")
        if saved_output_device and saved_output_device in output_device_names:
            self.output_device_combo.setCurrentText(saved_output_device)
        self.output_device_combo.currentTextChanged.connect(self._on_output_device_clicked)
        ######### Add widgets to speech groupbox widget #########
        speech_groupbox_layout.addWidget(speech_provider_label)
        speech_groupbox_layout.addWidget(self.speech_provider_combo)
        speech_groupbox_layout.addWidget(self.piper_model_button)
        speech_groupbox_layout.addWidget(self.piper_backend_button)
        speech_groupbox_layout.addWidget(self.polly_fallback_checkbox)
        speech_groupbox_layout.addWidget(self.fallback_voice_combo)
        speech_groupbox_layout.addWidget(self.local_voice_note)
        speech_groupbox_layout.addWidget(extra_tags_label)
        speech_groupbox_layout.addWidget(self.extra_tags_combo)
        speech_groupbox_layout.addWidget(speech_voice_label)
        speech_groupbox_layout.addWidget(self.speech_voice_combo)
        speech_groupbox_layout.addWidget(speech_pitch_label)
        speech_groupbox_layout.addWidget(self.speech_pitch_slider)
        speech_groupbox_layout.addWidget(output_device_label)
        speech_groupbox_layout.addWidget(self.output_device_combo)
        ######### Chatbox groupbox widget #########
        self.chatbox_status_checkbox = QtWidgets.QCheckBox("VRChat Chatbox")
        self.chatbox_status_checkbox.setChecked(self.config["CHATBOX"].getboolean("enabled"))
        self.chatbox_status_checkbox.stateChanged.connect(self._on_chatbox_status_clicked)
        self.chatbox_groupbox = QtWidgets.QGroupBox(self)
        self.chatbox_groupbox.setEnabled(self.config["CHATBOX"].getboolean("enabled"))
        saved_chatbox_settings_shown = self.config["CHATBOX"].getboolean("show more settings")
        self.chatbox_groupbox.setVisible(saved_chatbox_settings_shown)
        chatbox_groupbox_layout = QtWidgets.QVBoxLayout(self.chatbox_groupbox)
        ######### Font widget #########
        font_label = QtWidgets.QLabel("Font")
        self.font_combo = QtWidgets.QComboBox()
        self.font_combo.addItems(FONTS)
        self.font_combo.setCurrentText(self.config["CHATBOX"].get("font"))
        self.font_combo.currentTextChanged.connect(self._on_font_combo_clicked)
        ######### Chatbox animation widget #########
        self.chatbox_animation = QtWidgets.QCheckBox("Chatbox writing animation")
        self.chatbox_animation.setChecked(self.config["CHATBOX"].getboolean("animation"))
        self.chatbox_animation.stateChanged.connect(self._on_chatbox_animation_clicked)
        ######### Add widgets to chatbox groupbox widget #########
        chatbox_groupbox_layout.addWidget(font_label)
        chatbox_groupbox_layout.addWidget(self.font_combo)
        chatbox_groupbox_layout.addWidget(self.chatbox_animation)
        self.keyword_additions_checkbox = QtWidgets.QCheckBox("Enable keyword text / emoji additions")
        self.keyword_additions_checkbox.setChecked(self.config["CHATBOX"].getboolean("keyword_additions"))
        self.keyword_additions_checkbox.toggled.connect(self._on_keyword_additions_changed)
        chatbox_groupbox_layout.addWidget(self.keyword_additions_checkbox)
        ######### Beep option widget #########
        self.beep_status_checkbox = QtWidgets.QCheckBox("Beep while recognizing")
        self.beep_status_checkbox.setChecked(self.config["APP"].getboolean("beep"))
        self.beep_status_checkbox.stateChanged.connect(self._on_beep_option_clicked)
        ######### Activate button #########
        self.toggle_activate_button = QtWidgets.QPushButton(self)
        self.toggle_activate_button.setMinimumHeight(40)
        self._update_activate_button()
        self.toggle_activate_button.clicked.connect(self._update_activate_button)
        self.toggle_activate_button.clicked.connect(self.toggle_thread)
        ######### Delete Chatbox button #########
        chatbox_delete_button = QtWidgets.QPushButton(self, text="Clear Chatbox text")
        chatbox_delete_button.setStyleSheet("font-weight: bold")
        chatbox_delete_button.clicked.connect(self._on_chatbox_delete_button_clicked)
        ######### Log widget #########
        self.log_line_edit = QtWidgets.QLabel(self)
        outer_layout.setMenuBar(menu_bar)
        main_layout.addWidget(banner)
        main_layout.addWidget(tips_label)
        self.manual_text = QtWidgets.QPlainTextEdit()
        self.manual_text.setPlaceholderText("Paste a ChatGPT answer or type a message…")
        self.manual_text.setMinimumHeight(100)
        self.manual_text.setMaximumHeight(180)
        main_layout.addWidget(self.manual_text)
        self.manual_text.textChanged.connect(self._editor_changed)
        self.preview_checkbox = QtWidgets.QCheckBox("Preview recognition before sending")
        self.preview_checkbox.setChecked(self.config["PREVIEW"].getboolean("enabled"))
        self.preview_checkbox.toggled.connect(self._preview_settings_changed)
        main_layout.addWidget(self.preview_checkbox)
        delay_row = QtWidgets.QHBoxLayout()
        delay_row.addWidget(QtWidgets.QLabel("Auto-send delay (seconds):"))
        self.preview_delay = QtWidgets.QDoubleSpinBox()
        self.preview_delay.setRange(0, 60)
        self.preview_delay.setDecimals(1)
        self.preview_delay.setValue(self.config["PREVIEW"].getfloat("delay"))
        self.preview_delay.valueChanged.connect(self._preview_settings_changed)
        delay_row.addWidget(self.preview_delay)
        self.draft_status = QtWidgets.QLabel("Recognition and manual input share this editor.")
        self.draft_status.setWordWrap(True)
        main_layout.addWidget(self.draft_status)
        self.edit_message_button = QtWidgets.QPushButton("Edit message / pause auto-send")
        self.edit_message_button.clicked.connect(self.edit_pending_message)
        main_layout.addWidget(self.edit_message_button)
        self.manual_chatbox = QtWidgets.QCheckBox("Also send pasted text to VRChat Chatbox")
        main_layout.addWidget(self.manual_chatbox)
        self.speak_button = QtWidgets.QPushButton("Speak / send now")
        self.speak_button.clicked.connect(self.speak_manual_text)
        main_layout.addWidget(self.speak_button)
        self.stop_speech_button = QtWidgets.QPushButton("Stop speaking / cancel pending send")
        self.stop_speech_button.clicked.connect(self.stop_speaking)
        main_layout.addWidget(self.stop_speech_button)
        refresh_button = QtWidgets.QPushButton("Refresh audio devices")
        refresh_button.clicked.connect(self.refresh_devices)
        main_layout.addWidget(refresh_button)
        main_layout.addWidget(chatbox_delete_button)
        main_layout.addWidget(self.log_line_edit)
        main_layout.addWidget(self.progressbar)
        self.global_shortcuts_checkbox = QtWidgets.QCheckBox("Global hotkeys (also outside this app)")
        self.global_shortcuts_checkbox.setChecked(self.config["ROLEPLAY"].getboolean("global_hotkeys"))
        self.global_shortcuts_checkbox.toggled.connect(self._set_global_hotkeys)
        self.hotkey_state_label = QtWidgets.QLabel()
        self.hotkey_state_label.setWordWrap(True)
        self.hotkey_state_signal.connect(self.hotkey_state_label.setText)
        self.cards_by_key = {}
        def card(title, widgets, key):
            collapsed = self.config["UI"].getboolean("collapsed_" + key, fallback=key in ("voice", "chatbox", "endings"))
            group = CollapsibleCard(title, collapsed)
            group.collapsedChanged.connect(lambda value, name=key: self._save_collapsed(name, value))
            self.cards_by_key[key] = group
            for widget in widgets:
                group.content_layout.addWidget(widget)
            return group
        # Reparenting widgets removes them from their previous layout.
        input_card = card("Input, languages and controls", [
            input_device_label, self.input_device_combo, source_language_label, self.source_language_combo,
            target_language_label, self.target_language_combo, formality_label, self.formality_combo,
            self.beep_status_checkbox, self.global_shortcuts_checkbox, self.hotkey_state_label,
            self.toggle_activate_button, refresh_button], "inputs")
        message_card = card("Message preview and speech", [self.manual_text, self.preview_checkbox], "messages")
        message_card.content_layout.addLayout(delay_row)
        for widget in (self.draft_status, self.edit_message_button, self.manual_chatbox,
                       self.speak_button, self.stop_speech_button):
            message_card.content_layout.addWidget(widget)
        history_button = QtWidgets.QPushButton("Session history")
        history_button.clicked.connect(self.show_history)
        message_card.content_layout.addWidget(history_button)
        self.speech_groupbox.setVisible(True)
        self.chatbox_groupbox.setVisible(True)
        voice_card = card("Voice settings", [self.speech_status_checkbox, self.speech_groupbox], "voice")
        chatbox_card = card("VRChat Chatbox", [self.chatbox_status_checkbox,
                                             self.chatbox_groupbox, chatbox_delete_button], "chatbox")
        self.ending_text = QtWidgets.QLineEdit(self.config["ENDING"].get("text"))
        self.ending_text.setMaxLength(120)
        self.ending_text.setPlaceholderText(", poi or , desu")
        self.ending_text.textChanged.connect(self._ending_settings_changed)
        self.ending_frequency = QtWidgets.QSlider(Qt.Horizontal)
        self.ending_frequency.setRange(0, 100)
        self.ending_frequency.setValue(max(0, min(100, self.config["ENDING"].getint("frequency"))))
        self.ending_frequency.valueChanged.connect(self._ending_settings_changed)
        self.ending_frequency_label = QtWidgets.QLabel()
        note = QtWidgets.QLabel("Added once after translation, to speech and chatbox. 0% = never; 100% = always.")
        note.setWordWrap(True)
        ending_card = card("Random ending", [self.ending_text, self.ending_frequency_label, self.ending_frequency, note], "endings")
        self._update_ending_label()
        self.responsive_cards = ResponsiveCards([input_card, message_card, voice_card, chatbox_card, ending_card])
        main_layout.addWidget(self.responsive_cards)
        main_layout.addWidget(self.log_line_edit)
        main_layout.addWidget(self.progressbar)
        self.progressbar.setMaximumHeight(8)
        self.polly_fallback_checkbox.setText("Polly fallback (online; AWS charges)")
        self.manual_chatbox.setText("Send manual text to Chatbox")
        self.stop_speech_button.setText("Stop / cancel auto-send")
        self.edit_message_button.setText("Edit / pause auto-send")
        self.piper_backend_button.setText("Choose external Piper backend…")
        for label in self.findChildren(QtWidgets.QLabel):
            label.setWordWrap(True)
        for combo in self.findChildren(QtWidgets.QComboBox):
            combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(12)
            combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        ######### Append voices for the current provider #########
        self._append_voices_for_selected_provider()
        self.speech_voice_combo.setCurrentText(self.config["SPEECH"].get("voice"))
        self.speech_voice_combo.currentTextChanged.connect(self._on_voice_combo_clicked)
        ######### Checking which speech provider to use #########
        if self.config["SPEECH"].getboolean("enabled"):
            self._check_selected_speech_provider()
        self.toggle_activate_button.setFocus()

    def _save_collapsed(self, name, collapsed):
        self.config["UI"]["collapsed_" + name] = str(collapsed)
        self.save_config()

    def _update_ending_label(self):
        value = self.ending_frequency.value()
        description = "never" if value == 0 else "always" if value == 100 else "chance per utterance"
        self.ending_frequency_label.setText(f"{value}% — {description}")

    def _ending_settings_changed(self, *args):
        self.config["ENDING"]["text"] = self.ending_text.text()
        self.config["ENDING"]["frequency"] = str(self.ending_frequency.value())
        self._update_ending_label()
        self.save_config()

    def _record_history(self, entry):
        self.history.append(dict(entry))
        self.history = self.history[-50:]
        self.history_changed.emit()

    def clear_history(self):
        self.history.clear()
        self.history_changed.emit()

    def show_history(self):
        from vrchat_speech_assistant.history_dialog import HistoryDialog
        dialog = HistoryDialog(self)
        self.history_changed.connect(dialog.refresh)
        try:
            dialog.exec()
        finally:
            self.history_changed.disconnect(dialog.refresh)
            dialog.deleteLater()

    def load_history_source(self, entry):
        if self.pending_draft or (self.editor_dirty and self.manual_text.toPlainText().strip()):
            self.log_warning("Send or clear the unsent draft before loading a history entry.")
            return False
        self.preview_timer.stop()
        self.countdown_timer.stop()
        self.manual_text.setPlainText(entry["source"])
        self.cards_by_key["messages"].set_collapsed(False)
        self.manual_text.setFocus()
        return True

    def replay_history(self, entry):
        if self.output_busy:
            self.log_warning("Speech is busy. Stop or wait before replaying.")
            return False
        if self.pending_draft or self.editor_dirty:
            self.log_warning("Send or clear the unsent draft before replaying history.")
            return False
        if not entry["result"]:
            return False
        return bool(self._start_output(entry["result"], self.manual_chatbox.isChecked(), manual=True,
                                       already_translated=True, apply_ending=False))

    def _init_translator(self):
        api_key = self.config["API"].get("deepl_api_key") or _config.DEEPL_API_KEY
        self.translator = test_deepl(api_key)
        if not self.translator:
            self._disable_target_language_combo()

    def _map_command(self, address, callback):
        dispatcher.map(address, lambda *args: self.command_signal.emit(lambda: callback(*args)))

    def _init_server(self):
        def thread_server():
            with contextlib.suppress(OSError):
                self.osc_server.serve_forever()

        self._map_command("/port", self._server_update_client_port)
        self._map_command("/source_language", self._server_change_source_language)
        self._map_command("/target_language", self._server_change_target_language)
        self._map_command("/formality", self._server_change_formality)
        self._map_command("/roleplay", lambda _, action: self.roleplay_action(action))
        self._map_command("/speech", self._server_toggle_speech)
        self._map_command("/speech_provider", self._server_change_speech_provider)
        self._map_command("/tag", self._server_change_extra_tags)
        self._map_command("/voice", self._server_change_voice)
        self._map_command("/pitch", self._server_change_voice_pitch)
        self._map_command("/input", self._server_change_input_device)
        self._map_command("/output", self._server_change_output_device)
        self._map_command("/chatbox", self._server_toggle_chatbox)
        self._map_command("/animation", self._server_toggle_chatbox_animation)
        self._map_command("/font", self._server_change_font)
        self._map_command("/beep", self._server_toggle_recognizer_beep)
        self._map_command("/enabled", self._server_toggle_thread)
        thread = Thread(target=thread_server, daemon=True)
        thread.start()

    def edit_roleplay(self):
        from vrchat_speech_assistant.roleplay_dialog import RoleplayDialog
        RoleplayDialog(self).exec()

    def _set_global_hotkeys(self, enabled):
        self.config["ROLEPLAY"]["global_hotkeys"] = str(enabled)
        self.save_config()
        self._init_hotkeys()

    def _hotkey_report(self, message):
        logger.warning(message)
        self.status_signal.emit("warning", message)

    def _init_hotkeys(self):
        if self.global_hotkeys:
            self.global_hotkeys.stop()
            self.global_hotkeys = None
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.shortcuts = []
        settings = self.config["ROLEPLAY"]
        self.global_shortcuts_checkbox.blockSignals(True)
        self.global_shortcuts_checkbox.setChecked(settings.getboolean("global_hotkeys"))
        self.global_shortcuts_checkbox.blockSignals(False)
        bindings = {}
        seen = set()
        for action in ACTIONS:
            key = settings.get("key_" + action, DEFAULT_HOTKEYS[action])
            if key:
                try:
                    canonical = parse_hotkey(key)
                    if canonical in seen:
                        raise ValueError("Duplicate hotkey")
                    seen.add(canonical)
                    bindings[action] = key
                except ValueError:
                    self.log_warning("Invalid hotkey for " + action + "; edit Roleplay settings.")
        if settings.getboolean("global_hotkeys") and sys.platform == "win32":
            self.global_hotkeys = GlobalHotkeys(
                bindings, lambda action: self.command_signal.emit(lambda: self.roleplay_action(action)),
                self._hotkey_report,
                ready=lambda count, total: self.hotkey_state_signal.emit(f"Global shortcuts registered: {count}/{total}"))
            self.global_hotkeys.start()
        else:
            self.hotkey_state_signal.emit("App-focused shortcuts only" if not settings.getboolean("global_hotkeys")
                                          else "Global shortcuts require Windows; app-focused shortcuts active here")
            for action, key in bindings.items():
                shortcut = QtGui.QShortcut(QtGui.QKeySequence(key), self)
                shortcut.setContext(Qt.ApplicationShortcut)
                shortcut.setAutoRepeat(False)
                shortcut.activated.connect(lambda name=action: self.roleplay_action(name))
                self.shortcuts.append(shortcut)

    def roleplay_action(self, action):
        if self._closing:
            return
        settings = self.config["ROLEPLAY"]
        if action == "stop_speaking":
            self.stop_speaking()
        elif action == "switch_language":
            self.switch_language()
        elif action == "cycle_personality":
            names = list(PERSONALITIES)
            current = settings.get("personality", "Neutral")
            name = names[(names.index(current) + 1) % len(names)] if current in names else names[0]
            settings["personality"] = name
            settings["delivery"] = PERSONALITIES[name][0]
            self.save_config()
            self.log_info("Personality: " + name)
        elif action == "cycle_delivery":
            modes = list(DELIVERIES)
            if self.config["SPEECH"].get("provider") != "Amazon Polly":
                modes.remove("Confidential whisper")
            current = settings.get("delivery")
            mode = modes[(modes.index(current) + 1) % len(modes)] if current in modes else "Normal"
            settings["delivery"] = mode
            self.save_config()
            self.log_info("Delivery: " + mode)
        elif action == "toggle_listener":
            self.toggle_thread()
        elif action in ACTIONS[:4] or action == "speak_paste":
            if self.output_busy:
                self.log_warning("Speech is busy; announcement was not queued.")
                return
            if action == "speak_paste":
                self.speak_manual_text()
            else:
                personality = settings.get("personality", "Neutral")
                if personality not in PERSONALITIES:
                    personality = "Neutral"
                text = settings.get("phrase_" + action, "").strip() or announcement(personality, action)
                self._start_output(text, self.config["CHATBOX"].getboolean("enabled"), manual=True)

    def _on_source_language_combo_clicked(self, current_text: str):
        self.recognition_epoch += 1
        self.config["SPEECH"]["source_language"] = current_text
        self.save_config()
        # Disable target language combo if translator attribute is None
        if not self.translator:
            self._disable_target_language_combo()

    def _on_target_language_combo_clicked(self, current_text: str):
        self.config["SPEECH"]["target_language"] = current_text
        self.save_config()
        # Append voices for the current provider
        self._append_voices_for_selected_provider()
        self._check_selected_speech_provider()

    def _on_formality_combo_clicked(self, current_text: str):
        self.config["TRANSLATOR"]["formality"] = current_text
        self.save_config()

    def _on_speech_status_checkbox_clicked(self, checked: int):
        if checked == 2:
            self.speech_groupbox.setEnabled(True)
            self.config["SPEECH"]["enabled"] = "True"
            # Checking which speech provider to use
            self._check_selected_speech_provider()
        else:
            self.speech_groupbox.setEnabled(False)
            if self.chatbox_status_checkbox.checkState() == Qt.CheckState.Unchecked:
                self.toggle_activate_button.setEnabled(False)
            self.speech_provider = None
            self.config["SPEECH"]["enabled"] = "False"
        self.save_config()

    def _on_speech_show_more_options_clicked(self, checked):
        self.speech_groupbox.setVisible(checked == 2)
        self.config["SPEECH"]["show more settings"] = str(checked == 2)
        self.save_config()

    def _on_chatbox_show_more_options_clicked(self, checked):
        self.chatbox_groupbox.setVisible(checked == 2)
        self.config["CHATBOX"]["show more settings"] = str(checked == 2)
        self.save_config()

    def _on_speech_provider_combo_clicked(self, current_text: str):
        self.config["SPEECH"]["provider"] = current_text
        self.save_config()
        # Checking which speech provider to use
        self._append_voices_for_selected_provider()
        self._check_selected_speech_provider()

    def _on_fallback_changed(self, checked):
        self.config["SPEECH"]["polly_fallback"] = str(checked)
        self.save_config()
        self._check_selected_speech_provider()

    def _on_fallback_voice_changed(self, voice):
        self.config["SPEECH"]["fallback_voice"] = voice
        if voice:
            self.config["SPEECH"]["fallback_voice_" + self.config["SPEECH"].get("target_language")] = voice
        self.save_config()
        self._check_selected_speech_provider()

    def choose_piper_backend(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Piper executable", "", "Executables (*.exe);;All files (*)")
        if path:
            self.config["SPEECH"]["piper_executable"] = path
            self.save_config()
            self._check_selected_speech_provider()

    def choose_piper_model(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Piper voice", "", "Piper models (*.onnx)")
        if path:
            if not Path(path + ".json").is_file():
                self.log_error("The matching .onnx.json file must be beside the voice model.")
                return
            self.config["SPEECH"]["piper_model"] = path
            self.config["SPEECH"]["piper_model_" + self.config["SPEECH"].get("target_language")] = path
            self._append_voices_for_selected_provider()
            self._check_selected_speech_provider()

    def _on_keyword_additions_changed(self, enabled):
        self.config["CHATBOX"]["keyword_additions"] = str(enabled)
        self.save_config()

    def _on_extra_tags_combo_clicked(self, current_text: str):
        self.extra_tags["whispered"] = current_text == "Whispered"

    def _on_speech_pitch_value_changed(self, current_value: int):
        self.log_line_edit.setText(f"Voice pitch: {str(current_value)}%")
        self.config["SPEECH"]["pitch"] = str(current_value)
        self.save_config()
        # Config extra tags
        if current_value != 0:
            self.extra_tags["pitch"] = current_value
        elif current_value == 0 and self.extra_tags.get("pitch"):
            del self.extra_tags["pitch"]

    def _on_input_device_clicked(self, current_text: str):
        if self.is_listener_running:
            self.stop_listener()
            self.recover_listener = True
        self.capture_retry_after = 0
        self.config["APP"]["input_device"] = current_text
        self.save_config()

    def _on_output_device_clicked(self, current_text: str):
        self.config["SPEECH"]["output_device"] = current_text
        self.save_config()

    def _on_chatbox_status_clicked(self, checked: int):
        if checked == 2:
            self.chatbox_groupbox.setEnabled(True)
            self.clear_log()
            self.config["CHATBOX"]["enabled"] = "True"
            self.toggle_activate_button.setEnabled(True)
            # Checking which speech provider to use
            if self.config["SPEECH"].getboolean("enabled"):
                self._check_selected_speech_provider()
        else:
            self.chatbox_groupbox.setEnabled(False)
            self.config["CHATBOX"]["enabled"] = "False"
            # Disable the toggle activate button if the speech status checkbox is unchecked
            if self.speech_status_checkbox.checkState() == Qt.CheckState.Unchecked:
                self.toggle_activate_button.setEnabled(False)
        self.save_config()

    def _on_font_combo_clicked(self, current_text: str):
        self.config["CHATBOX"]["font"] = current_text
        self.save_config()

    def _on_chatbox_animation_clicked(self, checked: int):
        self.config["CHATBOX"]["animation"] = "True" if checked == 2 else "False"
        self.save_config()

    def _on_beep_option_clicked(self, checked: int):
        self.config["APP"]["beep"] = "True" if checked == 2 else "False"
        self.save_config()

    def _voice_key(self, provider, language):
        return "voice_choice_" + provider + "_" + language

    def _remember_voice(self):
        if self.voice_scope and self.speech_voice_combo.currentText():
            provider, language = self.voice_scope
            key = self._voice_key(provider, language)
            if key not in self.config["SPEECH"]:
                self.config["SPEECH"][key] = self.speech_voice_combo.currentText()

    def _on_voice_combo_clicked(self, current_text):
        if not current_text or not self.voice_scope:
            return
        provider, language = self.voice_scope
        self.config["SPEECH"]["voice"] = current_text
        self.config["SPEECH"][self._voice_key(provider, language)] = current_text
        self.config["SPEECH"]["voice_" + language] = current_text
        self.save_config()

    def _on_chatbox_delete_button_clicked(self):
        write_chatbox(self.osc_client, None)

    def _server_update_client_port(self, _, port):
        self.osc_client._port = port

    def _server_change_source_language(self, _, language):
        self.source_language_combo.setCurrentText(language)

    def _server_change_target_language(self, _, language):
        self.target_language_combo.setCurrentText(language)

    def _server_change_formality(self, _, formality):
        self.formality_combo.setCurrentText(formality)

    def _server_toggle_speech(self, _, option):
        if option == 0:
            self.speech_status_checkbox.setChecked(False)
            return
        self.speech_status_checkbox.setChecked(True)

    def _server_change_speech_provider(self, _, provider):
        for item in range(self.speech_provider_combo.count()):
            item_text = self.speech_provider_combo.itemText(item)
            if item_text.startswith(provider):
                self.speech_provider_combo.setCurrentText(item_text)
                return

    def _server_change_extra_tags(self, _, tag):
        self.extra_tags_combo.setCurrentText(tag)

    def _server_change_voice(self, _, voice):
        for item in range(self.speech_voice_combo.count()):
            item_text = self.speech_voice_combo.itemText(item)
            if item_text.startswith(voice):
                self.speech_voice_combo.setCurrentText(item_text)
                return

    def _server_change_voice_pitch(self, _, pitch):
        self.speech_pitch_slider.setValue(pitch)

    def _server_change_input_device(self, _, input_device):
        for item in range(self.input_device_combo.count()):
            item_text = self.input_device_combo.itemText(item)
            if item_text.startswith(input_device):
                self.input_device_combo.setCurrentText(item_text)
                return

    def _server_change_output_device(self, _, output_device):
        for item in range(self.output_device_combo.count()):
            item_text = self.output_device_combo.itemText(item)
            if item_text.startswith(output_device):
                self.output_device_combo.setCurrentText(item_text)
                return

    def _server_toggle_chatbox(self, _, option):
        if option == 0:
            self.chatbox_status_checkbox.setChecked(False)
            return
        self.chatbox_status_checkbox.setChecked(True)

    def _server_toggle_chatbox_animation(self, _, option):
        if option == 0:
            self.chatbox_animation.setChecked(False)
            return
        self.chatbox_animation.setChecked(True)

    def _server_change_font(self, _, font):
        for item in range(self.font_combo.count()):
            item_text = self.font_combo.itemText(item)
            if item_text.startswith(font):
                self.font_combo.setCurrentText(item_text)
                return

    def _server_toggle_recognizer_beep(self, _, option):
        if option == 0:
            self.beep_status_checkbox.setChecked(False)
            return
        self.beep_status_checkbox.setChecked(True)

    def _server_toggle_thread(self, _, option):
        if option == 0 and self.is_listener_running:
            self.toggle_thread()
        elif option == 1 and not self.is_listener_running:
            self.toggle_thread()

    def _update_activate_button(self):
        if self.recover_listener:
            self.toggle_activate_button.setText("CANCEL MICROPHONE RECOVERY")
        elif not self.is_listener_running:
            self.toggle_activate_button.setText("START LISTENING")
            self.toggle_activate_button.setStyleSheet("font-weight: bold")
        else:
            self.toggle_activate_button.setText("STOP LISTENING")
            self.toggle_activate_button.setStyleSheet(
                "background-color: red; color: black; font-weight: bold;"
            )

    def _disable_target_language_combo(self):
        if self.config["API"].get("deepl_api_key") or _config.DEEPL_API_KEY:
            self.log_error("DeepL API key is invalid or account usage limit reached.")
        else:
            self.log_info("Translation is off. Add a DeepL key to translate between languages.")
        self.target_language_combo.setEnabled(False)
        # Setting the target language to the same as the source language
        self.target_language_combo.setCurrentText(self.source_language_combo.currentText())
        self.config["SPEECH"]["target_language"] = self.source_language_combo.currentText()
        self.save_config()

    def _append_voices_for_selected_provider(self):
        provider_name = self.config["SPEECH"].get("provider")
        local = provider_name != "Amazon Polly"
        piper = provider_name == "Piper (offline)"
        self.piper_model_button.setVisible(piper)
        self.piper_backend_button.setVisible(piper)
        self.polly_fallback_checkbox.setVisible(local)
        self.fallback_voice_combo.setVisible(local)
        self.local_voice_note.setVisible(local)
        self.extra_tags_combo.setEnabled(not local)
        self.speech_pitch_slider.setEnabled(not local)
        self._remember_voice()
        language = self.config["SPEECH"].get("target_language")
        scope = (provider_name, language)
        saved_voice = self.config["SPEECH"].get(self._voice_key(*scope)) or self.config["SPEECH"].get("voice_" + language)
        if not saved_voice and (self.voice_scope is None or self.voice_scope == scope):
            saved_voice = self.config["SPEECH"].get("voice")
        self.voice_scope = scope
        if local and not piper and self.windows_speech is None:
            try:
                self.windows_speech = WindowsSpeech()
            except Exception:
                record_failure("Enumerate Windows voices", *sys.exc_info()[::2])
                self.windows_speech = UnavailableWindowsSpeech()
        voices = (list(self.windows_speech.voices) or ["No local voice available"]) if local and not piper else (
            VOICES["polly"].get(self.target_language_combo.currentText()) or ["None"])
        if piper:
            model = self.config["SPEECH"].get("piper_model")
            voices = [Path(model).stem if model else "Choose a Piper model"]
        self.speech_voice_combo.blockSignals(True)
        self.speech_voice_combo.clear()
        self.speech_voice_combo.addItems(voices)
        if saved_voice in voices:
            self.speech_voice_combo.setCurrentText(saved_voice)
        self.config["SPEECH"]["voice"] = self.speech_voice_combo.currentText()
        self.speech_voice_combo.blockSignals(False)
        saved_fallback = self.config["SPEECH"].get("fallback_voice_" + language) or self.config["SPEECH"].get("fallback_voice")
        self.fallback_voice_combo.blockSignals(True)
        self.fallback_voice_combo.clear()
        self.fallback_voice_combo.addItems(VOICES["polly"].get(self.target_language_combo.currentText()) or ["None"])
        self.fallback_voice_combo.setToolTip("Polly fallback voice for the selected target language")
        if self.fallback_voice_combo.findText(saved_fallback) >= 0:
            self.fallback_voice_combo.setCurrentText(saved_fallback)
        self.config["SPEECH"]["fallback_voice"] = self.fallback_voice_combo.currentText()
        self.fallback_voice_combo.blockSignals(False)
        self.save_config()

    def _check_selected_speech_provider(self):
        if not self.config["SPEECH"].getboolean("enabled"):
            self.speech_provider = None
            return
        if self.config["SPEECH"].get("provider") != "Amazon Polly":
            primary = (PiperSpeech(self.config["SPEECH"].get("piper_model"), self.config["SPEECH"].get("piper_executable", ""))
                       if self.config["SPEECH"].get("provider") == "Piper (offline)"
                       else self.windows_speech or UnavailableWindowsSpeech())
            self.speech_provider = primary
            if self.config["SPEECH"].getboolean("polly_fallback"):
                # Capture settings now; no AWS request is made until a local failure.
                access = self.config["API"].get("aws_access_key") or _config.AWS_ACCESS_KEY
                secret = self.config["API"].get("aws_secret_key") or _config.AWS_SECRET_KEY
                region = self.config["API"].get("aws_region")
                def fallback():
                    if not access or not secret:
                        raise RuntimeError("Configure AWS credentials for Polly fallback")
                    return Polly(access, secret, region)
                def notify():
                    record_failure("Local synthesis; trying Polly fallback", *sys.exc_info()[::2])
                    self.status_signal.emit("warning", "Local synthesis failed; using online Polly fallback.")
                self.speech_provider = SpeechWithFallback(
                    primary, fallback, self.config["SPEECH"].get("fallback_voice"), notify)
            self.toggle_activate_button.setEnabled(True)
            return
        # Amazon Polly
        if self.config["SPEECH"].get("provider") == "Amazon Polly":
            aws_access_key = self.config["API"].get("aws_access_key") or _config.AWS_ACCESS_KEY
            aws_secret_key = self.config["API"].get("aws_secret_key") or _config.AWS_SECRET_KEY
            region = self.config["API"].get("aws_region")
            valid = False
            try:
                if aws_access_key and aws_secret_key:
                    self.speech_provider = Polly(aws_access_key, aws_secret_key, region)
                    valid = self.speech_provider.test()
            except Exception:
                record_failure("Validate Polly credentials", *sys.exc_info()[::2])
            if not valid:
                self.speech_provider = None
                self.toggle_activate_button.setEnabled(False)
                self.log_error("Amazon AWS credentials are invalid or missing.")
            else:
                self.toggle_activate_button.setEnabled(True)
                self.clear_log()

    def _get_input_device_index(self, input_device_name):
        input_devices = {item["name"]: item["index"] for item in self.input_devices}
        return input_devices.get(input_device_name)

    def _voice_activity(self, activity: bool):
        chatbox_enabled = self.config["CHATBOX"].getboolean("enabled")
        self.progressbar.setMaximum(0 if activity else 100)
        if chatbox_enabled or not activity:
            try:
                self.osc_client.send_message("/chatbox/typing", bool(activity))
            except OSError:
                record_failure("Chatbox typing status", *sys.exc_info()[::2])

    @staticmethod
    def open_config_folder():
        """Open the configuration folder."""
        config_folder = CONFIG_FILE.parent
        config_folder.mkdir(parents=True, exist_ok=True)
        webbrowser.open(str(config_folder))

    @staticmethod
    def open_repository():
        """Open the repository of the current script in your default web browser."""
        webbrowser.open("https://github.com/AziAzazel/vrchat-speech-assistant-deluxe")

    def edit_config(self):
        """Open the configuration dialog."""
        config_dialog = ConfigDialog(self)
        config_dialog.exec()

    def save_config(self):
        """Save configuration changes to the configuration file."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open("w", encoding="utf-8") as config_file:
            self.config.write(config_file)

    def toggle_thread(self):
        """Start or stop the listener thread."""
        if not self.is_listener_running and not self.recover_listener:
            self.start_listener()
        else:
            self.stop_listener()
        self._update_activate_button()

    def refresh_devices(self):
        if self._closing or self.device_scan_busy:
            return
        self.device_scan_busy = True
        def scan():
            self.devices_signal.emit(self._detect_devices("input"), self._detect_devices("output"))
        Thread(target=scan, name="audio-device-refresh", daemon=True).start()

    def _apply_devices(self, inputs, outputs):
        self.device_scan_busy = False
        if self._closing:
            return
        old_index = self._get_input_device_index(self.config["APP"].get("input_device"))
        self.input_devices, self.output_devices = inputs, outputs
        for combo, devices, chosen in (
            (self.input_device_combo, inputs, self.config["APP"].get("input_device")),
            (self.output_device_combo, outputs, self.config["SPEECH"].get("output_device")),
        ):
            names = [d["name"] for d in devices]
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(names)
            if chosen:
                if chosen not in names:
                    combo.addItem(chosen)
                    combo.setItemData(combo.count() - 1, "Disconnected: reconnect or choose a device", Qt.ToolTipRole)
                combo.setCurrentText(chosen)
            combo.blockSignals(False)
        chosen_input = self.config["APP"].get("input_device")
        new_index = self._get_input_device_index(chosen_input)
        if self.is_listener_running and (new_index is None or new_index != old_index):
            self.stop_listener()
            self.recover_listener = True
        if self.recover_listener and new_index is not None and time.monotonic() >= self.capture_retry_after:
            if self.listener_session is None or not self.listener_session.thread.is_alive():
                self.start_listener()
        self._update_activate_button()
        chosen_output = self.config["SPEECH"].get("output_device")
        if chosen_output and chosen_output not in [d["name"] for d in outputs]:
            if self.output_busy:
                self.cancel_output.set()
            self.log_warning("Selected output is disconnected. Reconnect it or select another device; no audio was rerouted.")

    def _capture_failed(self, error, session):
        if self._closing or session is not self.listener_session or session.stopped.is_set():
            return
        record_failure("Microphone capture", type(error), error.__traceback__)
        self.is_listener_running = False
        self.recover_listener = True
        self.capture_retry_after = time.monotonic() + 5
        self.recognition_epoch += 1
        self._update_activate_button()
        self.log_warning("Microphone disconnected or failed. Waiting for device recovery.")
        self.refresh_devices()

    def switch_language(self):
        first, second = self.config["LANGUAGES"].get("first"), self.config["LANGUAGES"].get("second")
        if first not in GOOGLE or second not in GOOGLE or first not in DEEPL or second not in DEEPL:
            self.log_error("Choose supported quick-switch languages in Roleplay settings.")
            return
        self.recognition_epoch += 1
        self.edit_pending_message()
        current = self.config["SPEECH"].get("source_language")
        language = second if current == first else first
        previous_target = self.config["SPEECH"].get("target_language")
        self._remember_voice()
        for combo in (self.source_language_combo, self.target_language_combo):
            combo.blockSignals(True)
            combo.setCurrentText(language)
            combo.blockSignals(False)
        self.config["SPEECH"]["source_language"] = language
        self.config["SPEECH"]["target_language"] = language
        saved_voice = self.config["SPEECH"].get(self._voice_key(self.config["SPEECH"].get("provider"), language)) or self.config["SPEECH"].get("voice_" + language)
        if self.config["SPEECH"].get("provider") == "Piper (offline)" and self.config["SPEECH"].get("piper_model"):
            self.config["SPEECH"]["piper_model_" + previous_target] = self.config["SPEECH"].get("piper_model")
        saved_model = self.config["SPEECH"].get("piper_model_" + language)
        if saved_model:
            self.config["SPEECH"]["piper_model"] = saved_model
        if not saved_voice and self.config["SPEECH"].get("provider") == "Windows Speech" and self.windows_speech:
            hints = {"Polish": ("polish", "polski", "paulina"), "English": ("english", "david", "zira")}.get(language, ())
            saved_voice = next((name for name in self.windows_speech.voices if any(hint in name.lower() for hint in hints)), None)
        self._append_voices_for_selected_provider()
        if saved_voice and self.speech_voice_combo.findText(saved_voice) >= 0:
            self.speech_voice_combo.setCurrentText(saved_voice)
        self._check_selected_speech_provider()
        self.save_config()
        self.log_info("Language: " + language + ". Choose a matching voice/model if needed; pending draft paused.")

    def start_listener(self):
        """Start the listener thread."""
        if self.listener_session and self.listener_session.thread.is_alive():
            self.recover_listener = True
            return
        input_device_name = self.config["APP"].get("input_device")
        input_device_index = self._get_input_device_index(input_device_name)
        if input_device_index is None:
            self.recover_listener = True
            self.log_warning("Microphone missing. Reconnect it or choose another input device.")
            self.refresh_devices()
            return
        try:
            microphone = speech_recognition.Microphone(device_index=input_device_index)
            recognizer = speech_recognition.Recognizer()
            recognizer.operation_timeout = 15
            recognizer.pause_threshold = 0.5
            recognizer.non_speaking_duration = 0.5
            recognizer.dynamic_energy_threshold = False
            winsound.PlaySound(str(RESOURCES_PATH / "on.wav"), winsound.SND_ASYNC)
            session = BackgroundListener(
                recognizer, microphone, self.recognize,
                lambda error: self.capture_failed_signal.emit(error, session), generation=lambda: self.recognition_epoch)
            self.listener_session = session
            self.listener = self.listener_session.stop
            self.listener_session.start()
            self.is_listener_running = True
            self.recover_listener = False
            self.log_info("Listening...")
        except Exception:
            record_failure("Start microphone", *sys.exc_info()[::2])
            self.recover_listener = True
            self.capture_retry_after = time.monotonic() + 5
            self.log_error("Could not open microphone. Waiting for device recovery; see diagnostic logs.")

    def stop_listener(self):
        """Stop the listener thread."""
        winsound.PlaySound(str(RESOURCES_PATH / "off.wav"), winsound.SND_ASYNC)
        if self.listener:
            self.listener(wait_for_stop=False)
        self.recognition_epoch += 1
        self.recover_listener = False
        self.is_listener_running = False
        self.log_info("Listener stopped.")

    def recognize(self, recognizer: speech_recognition.Recognizer, audio: speech_recognition.Microphone, epoch=None):
        """Use Google's Speech Recognition API to recognize an audio file into a text string.

        Translate and speech the text if the attributes translator and / or speech_provider
        are not None.

        Note
        ----
        This method is intended to be used as an argument for the
        speech_recognition.Recognizer().listen_in_background function.

        Parameters
        ----------
        recognizer : `speech_recognition.Recognizer`
            A `Recognizer` instance from `speech_recognition` module used to perform speech recognition.
        audio : `speech_recognition.Microphone`
            A `Microphone` instance from `speech_recognition` module as the source of audio input.
        """
        epoch = self.recognition_epoch if epoch is None else epoch
        if self._closing or self.output_busy or self.pending_draft or self.editor_dirty or epoch != self.recognition_epoch:
            return  # Do not feed synthesized output back into the pipeline.
        try:
            source = self.config["SPEECH"].get("source_language")
            if self.config["APP"].getboolean("beep"):
                winsound.PlaySound(str(RESOURCES_PATH / "recognizing.wav"), winsound.SND_ASYNC)
            text = recognizer.recognize_google(audio, language=GOOGLE[source])
            if not self._closing and text.lower() not in ("stop", "stoppe", "staff"):
                if self.config["APP"].getboolean("beep"):
                    winsound.PlaySound(str(RESOURCES_PATH / "recognized.wav"), winsound.SND_ASYNC)
                self.recognized_signal.emit(text, epoch)
        except speech_recognition.UnknownValueError:
            self.status_signal.emit("warning", "The voice recognition did not understand.")
        except Exception:
            record_failure("Recognition", *sys.exc_info()[::2])
            self.status_signal.emit("error", "Recognition failed. See diagnostic logs.")

    def _submit_recognized(self, text, epoch=None):
        if epoch is not None and epoch != self.recognition_epoch:
            return
        if self._closing or self.output_busy or self.pending_draft or self.editor_dirty:
            return
        if not self.preview_checkbox.isChecked():
            self._start_output(text, self.config["CHATBOX"].getboolean("enabled"))
            return
        self.pending_draft = True
        self.cards_by_key["messages"].set_collapsed(False)
        self.loading_editor = True
        self.manual_text.setPlainText(text)
        scroll = self.findChild(QtWidgets.QScrollArea)
        if scroll:
            scroll.ensureWidgetVisible(self.manual_text)
        self.loading_editor = False
        self.editor_dirty = False
        delay = self.preview_delay.value()
        self.draft_deadline = time.monotonic() + delay
        self.preview_timer.start(round(delay * 1000))
        self.countdown_timer.start(100)
        self._update_countdown()

    def _update_countdown(self):
        if self.preview_timer.isActive():
            self.draft_status.setText(f"Auto-send in {max(0, self.draft_deadline - time.monotonic()):.1f}s — click Edit or type to pause.")

    def _preview_settings_changed(self, *args):
        self.config["PREVIEW"]["enabled"] = str(self.preview_checkbox.isChecked())
        self.config["PREVIEW"]["delay"] = str(self.preview_delay.value())
        self.save_config()
        if self.pending_draft:
            self.edit_pending_message()

    def _editor_changed(self):
        if not self.loading_editor:
            if not self.manual_text.toPlainText().strip():
                self.editor_dirty = False
                self.pending_draft = False
                self.preview_timer.stop()
                self.countdown_timer.stop()
                self.draft_status.setText("Editor cleared; recognition can fill the next draft.")
                return
            self.editor_dirty = True
            if self.pending_draft:
                self.edit_pending_message(focus=False)

    def edit_pending_message(self, focus=True):
        self.preview_timer.stop()
        self.countdown_timer.stop()
        if self.pending_draft:
            self.editor_dirty = True
            self.draft_status.setText("Auto-send paused. Edit, then click Speak / send now.")
        if focus:
            self.manual_text.setFocus()

    def speak_manual_text(self):
        self.preview_timer.stop()
        self.countdown_timer.stop()
        pending = self.pending_draft
        accepted = self._start_output(
            self.manual_text.toPlainText(),
            self.config["CHATBOX"].getboolean("enabled") if pending else self.manual_chatbox.isChecked(),
            manual=not pending)
        if accepted:
            self.pending_draft = False
            self.editor_dirty = False
            self.draft_status.setText("Message submitted.")
        elif pending:
            self.edit_pending_message(focus=False)

    def stop_speaking(self):
        self.cancel_output.set()
        self.recognition_epoch += 1
        self.preview_timer.stop()
        self.countdown_timer.stop()
        if self.pending_draft:
            self.editor_dirty = True
        self.pending_draft = False
        self.draft_status.setText("Stopped. Draft retained; send it manually or clear the editor to resume recognition.")
        self._voice_activity(False)
        self.log_info("Output cancelled. Any in-flight cloud request will be discarded when it returns.")

    def _start_output(self, text, send_chatbox, manual=False, already_translated=False, apply_ending=True):
        if self._closing or self.output_busy:
            return
        if not text.strip():
            self.log_warning("Enter some text first.")
            return
        if len(text) > 2500:
            self.log_warning("Please split text into messages of at most 2500 characters.")
            return
        if manual and (not self.speech_provider
                       or not self.config["SPEECH"].getboolean("enabled")
                       or self.config["SPEECH"].get("voice") == "None"):
            self.log_error("Enable Speech and configure a working speech provider first.")
            return
        if self.speech_provider and self.config["SPEECH"].getboolean("enabled"):
            selected = self.config["SPEECH"].get("output_device")
            if not selected or selected not in [d["name"] for d in self.output_devices]:
                self.log_warning("Select or reconnect the output device, then send again. No audio was rerouted.")
                self.refresh_devices()
                return
        config = {section: dict(self.config[section]) for section in ("SPEECH", "TRANSLATOR", "CHATBOX")}
        provider, translator = self.speech_provider, self.translator
        tags, corrections = dict(self.extra_tags), dict(self.corrections)
        pronunciations = dict(self.pronunciations)
        ending_text = self.config["ENDING"].get("text")
        ending_frequency = self.config["ENDING"].getint("frequency") if apply_ending else 0
        roleplay = dict(self.config["ROLEPLAY"])
        delivery = roleplay.get("delivery", "Normal")
        if delivery == "Confidential whisper" and self.config["SPEECH"].get("provider") != "Amazon Polly":
            self.log_warning("Confidential whisper requires Polly. Choose Polly or another delivery mode.")
            return
        tags.update(DELIVERIES.get(delivery, {}))
        rules = dict(self.chatbox_rules) if self.config["CHATBOX"].getboolean("keyword_additions") else {}
        client = CancellableOSC(self.osc_client)
        event = threading.Event()
        self.cancel_output = event
        self.output_busy = True
        self.speak_button.setEnabled(False)
        self._voice_activity(True)

        self.history_sequence += 1
        entry = {"id": self.history_sequence, "time": datetime.now().strftime("%H:%M:%S"),
                 "source": text, "result": "", "spoken": "", "status": "failed",
                 "language": config["SPEECH"]["target_language"], "provider": config["SPEECH"]["provider"],
                 "voice": config["SPEECH"]["voice"]}
        def output():
            stage = "Nickname correction"
            try:
                result = text.strip() if already_translated else correct_nicknames(text.strip(), corrections)
                check_cancelled()
                corrected_source = result
                speech = config["SPEECH"]
                if not already_translated and translator and speech["source_language"] != speech["target_language"]:
                    stage = "Translation"
                    options = config["TRANSLATOR"]
                    result = translator.translate_text(
                        result, source_lang=DEEPL[speech["source_language"]].split("-")[0],
                        target_lang=DEEPL[speech["target_language"]],
                        split_sentences=int(options["split_sentences"]),
                        formality={"Default": "default", "Formal": "prefer_more", "Informal": "prefer_less"}[options["formality"]],
                    ).text
                check_cancelled()
                result = add_random_ending(result, ending_text, ending_frequency)
                spoken = spoken_delivery(correct_nicknames(result, pronunciations), tags)
                entry["result"], entry["spoken"] = result, spoken
                if provider and speech["voice"] != "None":
                    stage = "Synthesis/audio playback"
                    provider.speech(spoken, speech["voice"], speech["output_device"], tags)
                check_cancelled()
                if send_chatbox:
                    stage = "Chatbox output"
                    chatbox_text = decorate_chatbox(result, rules, corrected_source)
                    if roleplay.get("chatbox_tag", "false").lower() == "true":
                        tag = PERSONALITIES.get(roleplay.get("personality"), PERSONALITIES["Neutral"])[1]
                        if tag:
                            chatbox_text = tag + " " + chatbox_text
                    write_chatbox(client, chatbox_text, font=config["CHATBOX"]["font"],
                                  chunk_length=25 if config["CHATBOX"]["animation"].lower() == "true" else 0)
                entry["status"] = "completed"
                logger.info("Output completed; manual=%s; chatbox=%s", manual, send_chatbox)
                self.status_signal.emit("info", "Output completed.")
            except OutputCancelled:
                entry["status"] = "cancelled"
                self.status_signal.emit("info", "Speech stopped; unsent chatbox output cancelled.")
            except Exception:
                if stage == "Synthesis/audio playback":
                    self.output_failed_signal.emit()
                record_failure(stage, *sys.exc_info()[::2])
                self.status_signal.emit("error", stage + " failed. See diagnostic logs.")
            finally:
                self.history_entry_signal.emit(entry)
                self.finished_signal.emit()

        def scoped_output():
            with output_scope(event):
                output()
        Thread(target=scoped_output, name="speech-output", daemon=True).start()
        return True

    def _finish_output(self):
        self.output_busy = False
        self.speak_button.setEnabled(True)
        self._voice_activity(False)

    def edit_nicknames(self):
        self._edit_text_rules("nicknames")

    def edit_chatbox_rules(self):
        self._edit_text_rules("chatbox")

    def edit_pronunciations(self):
        self._edit_text_rules("pronunciation")

    def _edit_text_rules(self, kind):
        chatbox = kind == "chatbox"
        pronunciation = kind == "pronunciation"
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Pronunciation dictionary — speech only" if pronunciation else "Chatbox keyword additions" if chatbox else "Nickname corrections")
        layout = QtWidgets.QVBoxLayout(dialog)
        description = QtWidgets.QLabel(
            "Keyword → appended text / emoji / link (chatbox only; images cannot be embedded)"
            if chatbox else "Displayed word → spoken pronunciation (after translation; chatbox unchanged)" if pronunciation
            else "Recognized name → replacement (before translation and speech)")
        description.setWordWrap(True)
        layout.addWidget(description)
        dialog.resize(650, 420)
        table = QtWidgets.QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Keyword", "Append text / emoji / link"] if chatbox else ["Displayed word", "Spoken pronunciation"] if pronunciation else ["Recognized phrase", "Correct name"])
        layout.addWidget(table)
        for key, value in (self.chatbox_rules if chatbox else self.pronunciations if pronunciation else self.corrections).items():
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(key))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(value))
        add = QtWidgets.QPushButton("Add rule")
        add.clicked.connect(lambda: table.insertRow(table.rowCount()))
        layout.addWidget(add)
        layout.addWidget(QtWidgets.QLabel("Clear a phrase to remove its correction."))
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            corrections = {}
            for row in range(table.rowCount()):
                key, value = table.item(row, 0), table.item(row, 1)
                if key and key.text().strip() and value:
                    corrections[key.text().strip()] = value.text()
            try:
                path = DATA_DIR / ("chatbox-rules.json" if chatbox else "pronunciation.json" if pronunciation else "nicknames.json")
                temporary = path.with_suffix(".tmp")
                temporary.write_text(json.dumps(corrections, ensure_ascii=False, indent=2), encoding="utf-8")
                temporary.replace(path)
                if chatbox:
                    self.chatbox_rules = corrections
                elif pronunciation:
                    self.pronunciations = corrections
                else:
                    self.corrections = corrections
            except OSError:
                record_failure("Save text rules", *sys.exc_info()[::2])
                self.log_error("Could not save text rules. See diagnostic logs.")

    @staticmethod
    def open_logs():
        webbrowser.open((DATA_DIR / "logs").as_uri())

    def translate(self, text: str) -> str:
        """Use DeepL's API to translate a text.

        Parameters
        ----------
        text : str
            The text to be translated.

        Returns
        -------
        str
            The translated text.
        """
        source_language = DEEPL[self.config["SPEECH"].get("source_language")].split("-")[0]
        target_language = DEEPL[self.config["SPEECH"].get("target_language")]
        split_sentences = self.config["TRANSLATOR"].getint("split_sentences")
        formality = self.config["TRANSLATOR"].get("formality")
        formality_mapping = {"Default": "default", "Formal": "prefer_more", "Informal": "prefer_less"}
        translated_text = self.translator.translate_text(
            text,
            split_sentences=split_sentences,
            formality=formality_mapping[formality],
            source_lang=source_language,
            target_lang=target_language,
        ).text
        self.log_info(f"Translated: {translated_text}")
        return translated_text

    def log_info(self, text: str):
        self.status_signal.emit("info", text)

    def log_warning(self, text: str):
        self.status_signal.emit("warning", text)

    def log_error(self, text: str):
        self.status_signal.emit("error", text)

    def _show_status(self, level, text):
        self.clear_log()
        color = {"info": "", "warning": "orange", "error": "#cd3131"}[level]
        self.log_line_edit.setText(text)
        self.log_line_edit.setStyleSheet(f"color: {color}" if color else "")
        if color:
            self.progressbar.setStyleSheet(f"border-style: none; background-color: {color}")

    def clear_log(self):
        """Clears the current log and resets the progress bar color."""
        self.log_line_edit.clear()
        self.progressbar.setStyleSheet("border-style: none")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "ui_ready", False):
            self.geometry_timer.start(250)

    def _save_window_size(self):
        if not self.ui_ready or self.isMinimized():
            return
        size = self.normalGeometry().size() if self.isMaximized() else self.size()
        self.config["UI"].update(width=str(size.width()), height=str(size.height()), maximized=str(self.isMaximized()))
        self.save_config()

    # pylint: disable=invalid-name, missing-function-docstring
    def closeEvent(self, event):
        if self.output_busy:
            self.log_warning("Wait for speech output to finish before closing.")
            event.ignore()
            return
        self._save_window_size()
        self.geometry_timer.stop()
        self._closing = True
        self.preview_timer.stop()
        self.countdown_timer.stop()
        self.device_timer.stop()
        if self.global_hotkeys:
            self.global_hotkeys.stop()
        if self.listener:
            self.listener(wait_for_stop=False)
        self.osc_server.shutdown()
        self.osc_server.server_close()
        event.accept()  # Let the window close


if __name__ == "__main__":
    app = QtWidgets.QApplication()
    darkstyle.apply(app)
    vrc_speech_assistant_window = VRCSpeechAssistantWindow()
    vrc_speech_assistant_window.show()
    sys.exit(app.exec())
