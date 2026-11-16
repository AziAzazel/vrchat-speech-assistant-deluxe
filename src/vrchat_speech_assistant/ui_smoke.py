"""Checks shared by the frozen Windows and Linux application smoke tests."""
def verify_workspace(window, app):
    from vrchat_speech_assistant.shortcut_conflicts import known_conflicts
    assert window.tabs.count() == 6
    for width in (650, 1100, 1500, 650):
        window.resize(width, 800)
        app.processEvents()
        assert window.transport.columns == (4 if width >= 820 else 2)
        assert window.transport.geometry().bottom() < window.tabs.geometry().top()
        assert window.status_bar.geometry().top() > window.tabs.geometry().bottom()
    draft = window.manual_text.toPlainText()
    window.transport.compact.setChecked(True)
    app.processEvents()
    assert window.tabs.tabBar().isHidden()
    assert window.stop_speech_button.isVisible() and window.speak_button.isVisible()
    assert window.manual_text.toPlainText() == draft
    window.show_workspace_tab('History')
    assert not window.transport.compact.isChecked()
    assert window.history_view.isVisible()
    assert window.history_view.table.rowCount() == len(window.history)
    window.show_workspace_tab('Soundboard')
    assert window.soundboard_library.table.rowCount() == len(window.soundboard_presets)
    window.show_workspace_tab('Conversation')
    assert window.stop_speech_button.property('shortcut_action') == 'stop_speaking'
    assert len(window.language_preset_buttons) == 4
    assert known_conflicts('Ctrl+N') and known_conflicts('Alt+F4')
