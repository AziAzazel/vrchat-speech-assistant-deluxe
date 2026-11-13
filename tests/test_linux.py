"""Linux routing ownership, native settings and local control entry points."""
import json
import sys
from unittest.mock import Mock
import pytest
from vrchat_speech_assistant import linux_audio, audio_devices
from vrchat_speech_assistant.linux_launcher import send_action


def test_virtual_microphone_transaction_reuse_and_cleanup(monkeypatch):
    modules, sinks, sources, calls = [], [], [], []
    def pulse(*args):
        calls.append(args)
        if args == ('list', 'short', 'modules'):
            return '\n'.join(f"{m['index']}\t{m['name']}\t{m['argument']}\tn/a" for m in modules)
        if args[:3] == ('-f', 'json', 'list'):
            return json.dumps({'modules': modules, 'sinks': sinks, 'sources': sources}[args[3]])
        if args[0] == 'load-module':
            index = len(modules) + 1
            modules.append({'index': index, 'name': args[1], 'argument': args[2]})
            (sinks if args[1] == 'module-null-sink' else sources).append({'name': linux_audio.SINK if args[1] == 'module-null-sink' else linux_audio.SOURCE})
            return str(index)
        if args[0] == 'unload-module':
            return ''
        raise AssertionError(args)
    monkeypatch.setattr(linux_audio, 'pulse', pulse)
    route = linux_audio.VirtualMicrophone()
    route.create()
    route.create()
    assert len(route.owned) == 2
    reused = linux_audio.VirtualMicrophone()
    reused.create()
    reused.remove()
    assert not any(c[0] == 'unload-module' for c in calls)
    route.remove()
    assert [c for c in calls if c[0] == 'unload-module'] == [('unload-module', '2'), ('unload-module', '1')]


def test_virtual_microphone_rolls_back_failed_source(monkeypatch):
    calls = []
    def pulse(*args):
        calls.append(args)
        if args == ('list', 'short', 'modules'):
            return f'4\tmodule-null-sink\tsink_name={linux_audio.SINK} sink_properties=device.description={linux_audio.DESCRIPTION}\tn/a'
        if args[:3] == ('-f', 'json', 'list'):
            return json.dumps([{'index': 4, 'name': 'module-null-sink',
                'argument': f'sink_name={linux_audio.SINK} sink_properties=device.description={linux_audio.DESCRIPTION}'}] if args[3] == 'modules' else [])
        if args[0] == 'load-module':
            if args[1] == 'module-remap-source':
                raise RuntimeError('Source failed')
            return '4'
        return ''
    monkeypatch.setattr(linux_audio, 'pulse', pulse)
    with pytest.raises(RuntimeError, match='Source failed'):
        linux_audio.VirtualMicrophone().create()
    assert ('unload-module', '4') in calls


def test_virtual_microphone_never_unloads_replaced_module(monkeypatch):
    pulse = Mock(return_value='4\tmodule-null-sink\tsink_name=someone_else\tn/a')
    monkeypatch.setattr(linux_audio, 'pulse', pulse)
    route = linux_audio.VirtualMicrophone()
    route.owned = [('4', 'module-null-sink', 'our arguments')]
    route.remove()
    assert pulse.call_count == 1


def test_linux_output_names_come_from_sdl_not_alsa(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_devices, 'WINDOWS_AUDIO', False)
    context = Mock()
    context.get_device_count.return_value = 1
    context.get_device_info_by_index.return_value = {'name':'pulse', 'hostApi': 3, 'index': 0, 'maxInputChannels': 2, 'maxOutputChannels': 2}
    context.get_host_api_info_by_type.return_value = {'index': 3}
    import types
    monkeypatch.setitem(sys.modules, 'pyaudio', types.SimpleNamespace(PyAudio=Mock(return_value=context), paALSA=3))
    monkeypatch.setattr(audio_devices, 'sdl_output_devices', lambda: [{'name':'SDL virtual output', 'index':0}])
    report = tmp_path/'probe.json'
    audio_devices.write_device_probe(report)
    snapshot = json.loads(report.read_text())
    assert snapshot['inputs'][0]['name'] == 'pulse'
    assert snapshot['outputs'][0]['name'] == 'SDL virtual output'


@pytest.mark.parametrize('action', ['greeting', 'stop_speaking', 'switch_language', 'soundboard_31'])
def test_linux_global_action_uses_local_existing_osc_endpoint(monkeypatch, action):
    from pythonosc import udp_client
    factory = Mock()
    monkeypatch.setattr(udp_client, 'SimpleUDPClient', factory)
    send_action(action)
    factory.assert_called_once_with('127.0.0.1', 7001)
    factory.return_value.send_message.assert_called_once_with('/roleplay', action)


@pytest.mark.parametrize('action', ['soundboard_32', 'shell', 'soundboard_-1', '../stop_speaking'])
def test_linux_action_rejects_arbitrary_commands(action):
    with pytest.raises(ValueError):
        send_action(action)


def test_packaged_external_process_restores_host_library_path(monkeypatch):
    from vrchat_speech_assistant.platform_support import external_process_env
    monkeypatch.setattr(sys, 'platform', 'linux')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setenv('LD_LIBRARY_PATH', '/tmp/bundled-libraries')
    monkeypatch.setenv('LD_LIBRARY_PATH_ORIG', '/host/libraries')
    assert external_process_env()['LD_LIBRARY_PATH'] == '/host/libraries'
    assert 'LD_LIBRARY_PATH_ORIG' not in external_process_env()
    assert __import__('os').environ['LD_LIBRARY_PATH'] == '/tmp/bundled-libraries'


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='Linux native startup')
def test_native_linux_ui_defaults_and_disabled_windows_features(gui, monkeypatch, tmp_path):
    app, main = gui
    monkeypatch.setattr(main, 'IS_WINDOWS', False)
    monkeypatch.setattr(main, 'CONFIG_FILE', tmp_path/'config.ini')
    monkeypatch.setattr(main, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(main.VRCSpeechAssistantWindow, '_init_translator', lambda self: None)
    window = main.VRCSpeechAssistantWindow()
    try:
        assert window.config['SPEECH']['provider'] == 'Piper (offline)'
        assert not window.global_shortcuts_checkbox.isEnabled()
        assert not window.speech_provider_combo.model().item(0).isEnabled()
        assert len(window.favorite_reactions.buttons) == 6
        window.manual_text.setPlainText('A Linux draft 👀')
        assert window.chatbox_preview.pages == ['A Linux draft 👀']
        assert not window.play_soundboard({'key':'', 'text':'Hello', 'language':'English', 'provider':'Windows Speech', 'voice':'Windows voice', 'output':'Voice only'})
        assert 'unavailable on Linux' in window.log_line_edit.text()
    finally:
        window.close()
        app.processEvents()
