"""Conversation-first workspace with fixed transport controls and tab-local scrolling."""
from PySide6 import QtCore, QtWidgets
from vrchat_speech_assistant.button_shortcuts import attach_shortcut_menu
from vrchat_speech_assistant.language_presets import LANGUAGE_PRESETS
from vrchat_speech_assistant.history_dialog import HistoryDialog


class TransportBar(QtWidgets.QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(5)
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(window.toggle_activate_button, 1)
        controls.addWidget(window.stop_speech_button, 1)
        window.stop_speech_button.setText('STOP speech')
        window.stop_speech_button.setMinimumHeight(40)
        window.stop_speech_button.setStyleSheet('font-weight: bold; color: #ffaaaa;')
        self.voice_button = QtWidgets.QPushButton('Voice settings')
        self.voice_button.clicked.connect(lambda: window.show_workspace_tab('Voice & languages'))
        controls.addWidget(self.voice_button)
        self.compact = QtWidgets.QCheckBox('Compact')
        self.compact.setToolTip('Hide settings and preview for VR. Your current voice and Chatbox output options still apply.')
        controls.addWidget(self.compact)
        layout.addLayout(controls)
        self.summary = QtWidgets.QLabel()
        self.summary.setTextFormat(QtCore.Qt.PlainText)
        self.summary.setWordWrap(True)
        self.summary.setMinimumWidth(0)
        self.summary.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        layout.addWidget(self.summary)
        self.presets = QtWidgets.QGridLayout()
        self.columns = 0
        window.language_preset_buttons = {}
        for action in LANGUAGE_PRESETS:
            button = QtWidgets.QPushButton()
            button.setCheckable(True)
            button.setStyleSheet('QPushButton:checked { background: #294b66; border: 1px solid #6aabd6; font-weight: bold; }')
            button.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
            button.setMinimumHeight(30)
            button.clicked.connect(lambda checked=False, name=action: window.roleplay_action(name))
            attach_shortcut_menu(button, window, action)
            window.language_preset_buttons[action] = button
        layout.addLayout(self.presets)
        self.reflow()

    def reflow(self):
        columns = 4 if self.width() >= 820 else 2
        if columns == self.columns:
            return
        self.columns = columns
        while self.presets.count():
            self.presets.takeAt(0)
        for col in range(4):
            self.presets.setColumnStretch(col, 1 if col < columns else 0)
        for index, button in enumerate(self.window.language_preset_buttons.values()):
            self.presets.addWidget(button, index // columns, index % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()


def scroll_page(widget):
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    scroll.setWidget(widget)
    return scroll


def page_layout():
    page = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(page)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(8)
    return page, layout


class SectionGroupBox(QtWidgets.QGroupBox):
    """Keep the styled title clear of the first row at any application font."""

    def reserve_heading_space(self):
        if self.layout() is not None:
            # QGroupBox's styled title does not reliably contribute to the
            # layout's contents margins. Reserve its text height plus the
            # stylesheet's title padding/border and a gap explicitly.
            self.layout().setContentsMargins(12, self.fontMetrics().height() + 18, 12, 12)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QtCore.QEvent.FontChange, QtCore.QEvent.StyleChange):
            self.reserve_heading_space()


def form_group(title, rows):
    # The title is painted in the margin; reserve space only for titled cards,
    # not the untitled form containers nested inside Speech/Chatbox settings.
    group = SectionGroupBox(title) if title else QtWidgets.QGroupBox()
    form = QtWidgets.QFormLayout(group)
    if title:
        group.reserve_heading_space()
    form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
    for label, widget in rows:
        if label:
            form.addRow(label, widget)
        else:
            form.addRow(widget)
        widget.show()
    return group


def rebuild_group(group, rows):
    # Retain group identity/enabled state used by the speech/chatbox handlers.
    layout = group.layout()
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
    fields = form_group('', rows)
    fields.setFlat(True)
    layout.addWidget(fields)
    group.show()


def action_button(label, callback):
    button = QtWidgets.QPushButton(label)
    button.clicked.connect(callback)
    button.setMinimumHeight(32)
    return button


class SoundboardLibrary(QtWidgets.QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['Phrase / recording', 'Language', 'Output', 'Shortcut', 'Voice'])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.setColumnWidth(0, 200)
        layout.addWidget(self.table)
        actions = QtWidgets.QGridLayout()
        self.play = action_button('Play selected', self.play_selected)
        actions.addWidget(self.play, 0, 0)
        actions.addWidget(action_button('Manage phrases, recordings & SRT…', window.edit_soundboard), 0, 1)
        self.youtube = action_button('YouTube player…', window.open_youtube)
        from vrchat_speech_assistant.platform_support import IS_WINDOWS
        self.youtube.setEnabled(IS_WINDOWS)
        self.youtube.setToolTip('Windows: owned Edge audio player. Route browser audio using the Windows volume mixer.')
        actions.addWidget(self.youtube, 1, 0)
        actions.addWidget(action_button('Shortcuts & delivery…', window.edit_roleplay), 1, 1)
        layout.addLayout(actions)
        self.table.itemSelectionChanged.connect(self.update_play)
        self.refresh()

    def refresh(self):
        selected = self.table.currentRow()
        self.table.setRowCount(0)
        for preset in self.window.soundboard_presets:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, field in enumerate(('text', 'language', 'output', 'key', 'voice')):
                item = QtWidgets.QTableWidgetItem(preset.get(field, ''))
                item.setToolTip(preset.get(field, ''))
                self.table.setItem(row, column, item)
        if self.table.rowCount():
            self.table.selectRow(max(0, min(selected, self.table.rowCount()-1)))
        self.update_play()

    def update_play(self):
        self.play.setEnabled(self.table.currentRow() >= 0 and not self.window.output_busy)

    def play_selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.window.soundboard_presets):
            self.window.play_soundboard(self.window.soundboard_presets[row])


def build_workspace(window, outer, refresh_button, clear_button):
    w = window
    w.transport = TransportBar(w)
    outer.insertWidget(0, w.transport)
    w.tabs = QtWidgets.QTabWidget()
    w.tabs.setDocumentMode(True)
    w.tabs.tabBar().setExpanding(False)
    w.tabs.tabBar().setUsesScrollButtons(True)
    outer.insertWidget(1, w.tabs, 1)
    w.tab_pages = {}
    def add(name, page):
        w.tab_pages[name] = page
        w.tabs.addTab(page, name.replace('&', '&&'))

    conversation, layout = page_layout()
    w.manual_text.setMinimumHeight(95)
    w.manual_text.setMaximumHeight(300)
    layout.addWidget(w.manual_text, 1)
    actions = QtWidgets.QHBoxLayout()
    actions.addWidget(w.speak_button, 1)
    actions.addWidget(w.edit_message_button, 1)
    w.speak_button.setMinimumHeight(36)
    layout.addLayout(actions)
    layout.addWidget(w.draft_status)
    routes = QtWidgets.QWidget()
    routes.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
    w.draft_status.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
    route_layout = QtWidgets.QVBoxLayout(routes)
    route_layout.setContentsMargins(0, 0, 0, 0)
    route_layout.setSpacing(3)
    route_layout.addWidget(w.manual_chatbox)
    route_layout.addWidget(w.separate_chatbox)
    route_layout.addWidget(w.custom_chatbox_text)
    w.custom_chatbox_text.setMinimumHeight(50)
    w.custom_chatbox_text.setVisible(w.separate_chatbox.isChecked())
    w.separate_chatbox.toggled.connect(w.custom_chatbox_text.setVisible)
    layout.addWidget(routes)
    w.preview_toggle = QtWidgets.QCheckBox('Show Chatbox preview')
    w.preview_toggle.setChecked(w.config['UI'].getboolean('chatbox_preview_visible', fallback=False))
    layout.addWidget(w.preview_toggle)
    w.chatbox_preview.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
    layout.addWidget(w.chatbox_preview)
    w.preview_toggle.toggled.connect(w._workspace_preview_changed)
    w.chatbox_preview.changed.connect(w._update_preview_summary)
    # The full explanation remains on hover; do not spend two lines on every draft.
    w.chatbox_preview.note.hide()
    w.chatbox_preview.note.setToolTip('Preview does not send text; translation and random endings can change final pages.')
    reaction_title = QtWidgets.QHBoxLayout()
    title = QtWidgets.QLabel('Favorite reactions')
    title.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
    reaction_title.addWidget(title, 1)
    edit_favorites = action_button('Edit favorites…', w.edit_soundboard)
    reaction_title.addWidget(edit_favorites)
    layout.addLayout(reaction_title)
    w.favorite_reactions.note.hide()
    w.favorite_reactions.edit_button.hide()
    w.favorite_reactions.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
    layout.addWidget(w.favorite_reactions)
    w.conversation_scroll = scroll_page(conversation)
    add('Conversation', w.conversation_scroll)
    w.compact_details = [routes, w.preview_toggle, w.draft_status, edit_favorites]

    w.soundboard_library = SoundboardLibrary(w)
    add('Soundboard', w.soundboard_library)
    w.history_view = HistoryDialog(w, embedded=True)
    w.history_changed.connect(w.history_view.refresh)
    add('History', w.history_view)

    voice, voice_layout = page_layout()
    voice_layout.addWidget(form_group('Languages & translation', [
        ('Recognition / input', w.source_language_combo), ('Output / translation', w.target_language_combo),
        ('DeepL formality', w.formality_combo),
        ('', action_button('Edit language presets & their shortcuts…', lambda: w.edit_roleplay('language_preset_1')))]))
    voice_layout.addWidget(w.speech_status_checkbox)
    rebuild_group(w.speech_groupbox, [('Provider', w.speech_provider_combo), ('Voice', w.speech_voice_combo),
        ('Delivery', w.extra_tags_combo), ('Pitch', w.speech_pitch_control),
        ('', w.piper_model_button), ('', w.piper_backend_button), ('', w.polly_fallback_checkbox),
        ('Fallback voice', w.fallback_voice_combo), ('', w.local_voice_note), ('', w.polly_capability_label)])
    voice_layout.addWidget(w.speech_groupbox)
    voice_layout.addWidget(form_group('Recognition preview', [('', w.preview_checkbox), ('Auto-send delay (seconds)', w.preview_delay)]))
    voice_layout.addWidget(w.chatbox_status_checkbox)
    rebuild_group(w.chatbox_groupbox, [('Chatbox style', w.font_combo), ('', w.keyword_additions_checkbox), ('', clear_button)])
    voice_layout.addWidget(w.chatbox_groupbox)
    voice_layout.addStretch()
    add('Voice & languages', scroll_page(voice))

    roleplay, role_layout = page_layout()
    role_layout.addWidget(form_group('Roleplay & pronunciation', [
        ('', action_button('Personality, expressive delivery & shortcuts…', w.edit_roleplay)),
        ('', action_button('Nickname corrections…', w.edit_nicknames)),
        ('', action_button('Pronunciation dictionary…', w.edit_pronunciations)),
        ('', action_button('Keyword text / emoji additions…', w.edit_chatbox_rules))]))
    role_layout.addWidget(form_group('Random phrase endings', [('Ending', w.ending_text),
        ('Frequency', w.ending_frequency), ('', w.ending_frequency_label)]))
    role_layout.addWidget(QtWidgets.QLabel('0% = never; 100% = every utterance. Added once to speech and Chatbox.'))
    role_layout.addStretch()
    add('Roleplay', scroll_page(roleplay))

    settings, settings_layout = page_layout()
    settings_layout.addWidget(form_group('Audio devices', [('Microphone', w.input_device_combo),
        ('Speech output', w.output_device_combo), ('', refresh_button), ('', w.beep_status_checkbox)]))
    settings_layout.addWidget(form_group('Providers & shortcuts', [
        ('', action_button('DeepL / AWS credentials…', w.edit_config)),
        ('', w.global_shortcuts_checkbox), ('', w.hotkey_state_label),
        ('', action_button('Edit shortcuts…', w.edit_roleplay)),
        ('', action_button('Open diagnostic logs', w.open_logs)),
        ('', action_button('Open settings folder', w.open_config_folder))]))
    from vrchat_speech_assistant.platform_support import IS_WINDOWS
    if not IS_WINDOWS:
        settings_layout.addWidget(action_button('Linux virtual microphone / routing…', w.edit_linux_audio))
    settings_layout.addStretch()
    add('Settings', scroll_page(settings))
    from vrchat_speech_assistant.live_studio import LiveStudio
    w.live_studio = LiveStudio(w)
    add('Live Voice Studio', scroll_page(w.live_studio))
    w.tabs.currentChanged.connect(lambda index: w.live_studio.activate()
                                 if w.tabs.currentWidget() is w.tab_pages['Live Voice Studio'] else None)
    w.transport.compact.toggled.connect(w._set_compact_mode)
    w.transport.compact.setChecked(w.config['UI'].getboolean('compact', fallback=False))
    w._apply_workspace_visibility()
    w._refresh_language_presets()
