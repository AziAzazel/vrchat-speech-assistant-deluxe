"""Packaged Linux GUI and real PulseAudio virtual-microphone loopback test."""
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import threading
import time
import wave


def smoke_test(report_path):
    from PySide6 import QtWidgets
    from vrchat_speech_assistant import darkstyle, __version__
    from vrchat_speech_assistant import main
    from vrchat_speech_assistant.audio_devices import get_device_snapshot
    from vrchat_speech_assistant.linux_audio import VirtualMicrophone, SINK, SOURCE, DESCRIPTION, pulse
    from vrchat_speech_assistant.platform_support import external_process_env
    from vrchat_speech_assistant.providers import read_ogg_file
    from vrchat_speech_assistant.output_control import output_scope
    from vrchat_speech_assistant.live_chatbox import split_pages
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import BlockingOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient
    checks = {'version': __version__}
    def stage(name):
        checks['stage'] = name
        Path(report_path).write_text(json.dumps(checks), encoding='utf-8')
    folder = Path(tempfile.mkdtemp(prefix='deluxe-native-linux-'))
    route = VirtualMicrophone()
    recorder = None
    window = None
    try:
        stage("virtual_microphone")
        route.create()
        assert any(d['name'] == SOURCE for d in json.loads(pulse('-f', 'json', 'list', 'sources')))
        checks['virtual_microphone'] = 'passed'
        stage("device_probe")
        snapshot = get_device_snapshot()
        assert snapshot['pid'] != os.getpid()
        assert any(d['name'] == DESCRIPTION for d in snapshot['outputs']), snapshot['outputs']
        assert snapshot['inputs'], 'No PortAudio input device (install libasound2-plugins).'
        checks['isolated_device_probe'] = 'passed'
        stage('real_audio_loopback')
        tone = folder/'tone.wav'
        rate = 22050
        with wave.open(str(tone), 'wb') as audio:
            audio.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            audio.writeframes(b''.join(struct.pack('<h', int(8000*math.sin(2*math.pi*440*i/rate))) for i in range(rate)))
        recorded = folder/'loopback.raw'
        with recorded.open('wb') as output:
            recorder = subprocess.Popen(['parec', '--device='+SOURCE, '--format=s16le', '--rate='+str(rate), '--channels=1'],
                stdout=output, stderr=subprocess.DEVNULL, env=external_process_env())
            time.sleep(.25)
            assert recorder.poll() is None
            with output_scope(threading.Event()):
                read_ogg_file(str(tone), DESCRIPTION)
            time.sleep(.25)
            recorder.terminate()
            recorder.wait(5)
            recorder = None
        raw = recorded.read_bytes()
        samples = struct.unpack('<'+'h'*(len(raw)//2), raw[:len(raw)//2*2])
        assert len(samples) > rate//4 and max(abs(n) for n in samples) > 500, 'Virtual microphone received no audible samples.'
        checks['real_sdl_to_virtual_microphone'] = 'passed'
        stage('gui')
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        darkstyle.apply(app)
        main.CONFIG_FILE = folder/'config.ini'
        main.DATA_DIR = folder
        window = main.VRCSpeechAssistantWindow()
        window.show()
        app.processEvents()
        assert window.config['SPEECH']['provider'] == 'Piper (offline)'
        assert not window.global_shortcuts_checkbox.isEnabled()
        assert len(window.favorite_reactions.buttons) == 6
        source = '👀 Linux text ' * 40
        window.manual_text.setPlainText(source)
        assert window.chatbox_preview.pages == split_pages(source)
        window.separate_chatbox.setChecked(True)
        window.custom_chatbox_text.setPlainText('*looks suspicious*')
        assert window.chatbox_preview.pages == ['*looks suspicious*']
        for width, columns in [(650,1), (1100,2), (1500,3), (650,1)]:
            window.resize(width,700)
            app.processEvents()
            assert window.responsive_cards.columns == columns
        checks['gui_and_shared_controls'] = 'passed'
        stage('osc_udp')
        received = threading.Event()
        dispatcher = Dispatcher()
        dispatcher.map('/chatbox/input', lambda *args: received.set())
        server = BlockingOSCUDPServer(('127.0.0.1',0), dispatcher)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            from chatbox_osc import write_chatbox
            write_chatbox(SimpleUDPClient(*server.server_address), 'Linux OSC test', font='Normal', chunk_length=0)
            assert received.wait(3)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(3)
        checks['real_osc_udp'] = 'passed'
        checks.pop('stage', None)
        Path(report_path).write_text(json.dumps(checks, indent=2), encoding='utf-8')
    finally:
        if recorder is not None:
            recorder.terminate()
            recorder.wait(5)
        if window is not None:
            window.close()
            app.processEvents()
        route.remove()
