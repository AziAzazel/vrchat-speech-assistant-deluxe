"""Offline and real Linux PortAudio/virtual-cable readiness checks."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid
import numpy as np


def verify_dsp():
    from vrchat_speech_assistant.live_settings import default_patch, builtin_presets
    from vrchat_speech_assistant.live_dsp import VoicePipeline, detect_pitch
    rate=48000;t=np.arange(rate)/rate;source=.1*np.sin(2*np.pi*220*t)
    assert abs(detect_pitch(source[:4096],rate)[0]-220)<1
    for name,patch in builtin_presets().items():
        pipeline=VoicePipeline(rate,'Low Latency',patch)
        result=np.concatenate([pipeline.process(source[i:i+256]) for i in range(0,len(source),256)])
        assert np.isfinite(result).all() and np.abs(result).max()<=.892,name
        assert np.sqrt(np.mean(result**2))>1e-5,name
    patch=default_patch();patch['effects']['gate']['enabled']=False
    patch['effects']['pitch'].update(enabled=True,semitones=12)
    engine=VoicePipeline(rate,'Low Latency',patch)
    output=np.concatenate([engine.process(source[i:i+256])[:,0] for i in range(0,len(source),256)])
    middle=output[12000:36000];frequency=np.argmax(abs(np.fft.rfft(middle*np.hanning(len(middle)))))*2
    assert abs(frequency-440)<4


def verify_linux_routing(directory):
    """Feed a synthetic microphone through the SAME worker used by the GUI.

    Capture the virtual output independently using PulseAudio, never infer
    success from a running PID or from internal DSP buffers alone.
    """
    from PySide6 import QtCore
    from vrchat_speech_assistant.live_controller import StudioController
    from vrchat_speech_assistant.live_settings import default_patch
    import soundfile as sf
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    tag='deluxe_studio_'+uuid.uuid4().hex[:8];modules=[];events=[];captures=[]
    controller=StudioController();controller.status.connect(events.append,QtCore.Qt.DirectConnection)
    previous=os.environ.get('ALSA_CONFIG_PATH');rate=48000
    def pulse(*args):
        return subprocess.check_output(['pactl',*args],stderr=subprocess.DEVNULL,text=True,timeout=10).strip()
    def wait_until(predicate,timeout=15):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.01)
        raise AssertionError('Studio readiness timed out: '+str([e for e in events if e.get('type')!='meters'][-3:]))
    def capture(name, frequency=None, duration=1.5, callback=None):
        target=directory/(name+'.raw');stream=target.open('wb')
        process=subprocess.Popen(['parec','--device='+tag+'_output.monitor','--format=float32le','--rate=48000',
                                  '--channels=1','--latency-msec=10'],stdout=stream,stderr=subprocess.DEVNULL)
        captures.append((process,stream));time.sleep(.15)
        try:
            if frequency:
                source=directory/'source.raw';source.write_bytes((.12*np.sin(2*np.pi*frequency*np.arange(int(rate*duration))/rate)).astype(np.float32).tobytes())
                with source.open('rb') as input_file:
                    feeder=subprocess.Popen(['pacat','--playback','--device='+tag+'_input','--format=float32le','--rate=48000',
                                             '--channels=1','--latency-msec=10'],stdin=input_file,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    try:feeder.wait(timeout=duration+8)
                    finally:
                        if feeder.poll() is None:feeder.kill();feeder.wait()
            elif callback:callback()
            else:time.sleep(duration)
            time.sleep(.25)
        finally:
            process.terminate();process.wait(timeout=3);stream.close();captures.remove((process,stream))
        data=np.fromfile(target,dtype=np.float32);assert len(data)>rate*.25,'No real output captured'
        window=data[len(data)//4:3*len(data)//4]
        fundamental=np.argmax(abs(np.fft.rfft(window*np.hanning(len(window)))))*rate/len(window)
        return {'frequency':float(fundamental),'rms':float(np.sqrt(np.mean(window*window))), 'peak':float(np.abs(data).max())}
    try:
        for suffix in ('input','output'):
            modules.append(pulse('load-module','module-null-sink','sink_name='+tag+'_'+suffix,'rate=48000'))
        alsa=directory/'studio-alsa.conf'
        alsa.write_text('</usr/share/alsa/alsa.conf>\n'
                        f'pcm.studio_input {{ type pulse device "{tag}_input.monitor" hint {{ show on description "Studio input" }} }}\n'
                        f'pcm.studio_output {{ type pulse device "{tag}_output" hint {{ show on description "Studio output" }} }}\n')
        os.environ['ALSA_CONFIG_PATH']=str(alsa)
        patch=default_patch();patch['effects']['gate']['enabled']=False;patch['effects']['pitch'].update(enabled=True,semitones=12)
        config={'patch':patch,'input':'ALSA | studio_input','output':'ALSA | studio_output','monitor_device':'','source':'Microphone',
                'rate':rate,'buffer':256,'mode':'Low Latency','channels':1,'monitor':False,'bypass':False,'mute':False,'ptt':False,'activation':False,'activation_db':-45}
        controller.start(config);wait_until(controller.ready.is_set,25);pid=controller.process.pid
        pitch=capture('live-pitch',220)
        assert abs(pitch['frequency']-440)<8 and pitch['rms']>.003,pitch
        patch=default_patch();patch['effects']['gate']['enabled']=False;patch['effects']['tune'].update(enabled=True,strength=100,retune=0,smoothing=0);patch['hard_tune']=True
        config=dict(config,patch=patch);controller.configure(config);time.sleep(.2)
        tune=capture('live-tune',450)
        assert abs(tune['frequency']-440)<8 and controller.process.pid==pid,tune
        controller.send({'type':'panic'});time.sleep(.2)
        panic=capture('live-panic',220,1)
        assert panic['peak']<1e-6,panic
        controller.send({'type':'resume'})
        patch=default_patch();patch['effects']['gate']['enabled']=False;patch['effects']['pitch'].update(enabled=True,semitones=12)
        config=dict(config,source='TTS',patch=patch);controller.ready.clear();controller.configure(config);wait_until(controller.ready.is_set)
        tts_path=directory/'tts-source.wav';sf.write(str(tts_path),.1*np.sin(2*np.pi*220*np.arange(rate*2)/rate),rate)
        record_path=Path(controller.folder.name)/'processed-test.wav'
        controller.send({'type':'record','enabled':True,'path':str(record_path)})
        from vrchat_speech_assistant.output_control import audio_delivery_scope
        from vrchat_speech_assistant.providers import read_ogg_file
        def tts():
            with audio_delivery_scope(controller.route_tts):read_ogg_file(str(tts_path),'This device must not be used')
        recorded=capture('live-tts',callback=tts)
        assert abs(recorded['frequency']-440)<8 and recorded['rms']>.003,recorded
        controller.send({'type':'record','enabled':False});wait_until(lambda:any(e.get('type')=='recorded' for e in events))
        audio,sample_rate=sf.read(str(record_path));assert len(audio)>sample_rate and np.max(np.abs(audio))>.01
        meters=[e for e in events if e.get('type')=='meters'];assert meters
        result={'microphone_pitch':pitch,'hard_tune':tune,'panic':panic,'tts':recorded,'recording':'passed',
                'same_process_for_parameter_changes':True,'reported_latency_ms':meters[-1]['latency_ms'],
                'dsp_ms_p95':float(np.percentile([e['dsp_ms'] for e in meters],95)),
                'dsp_load_p95':float(np.percentile([e['load'] for e in meters],95))}
        (directory/'live-studio-report.json').write_text(json.dumps(result,indent=2))
        return result
    finally:
        controller.close()
        if previous is None:os.environ.pop('ALSA_CONFIG_PATH',None)
        else:os.environ['ALSA_CONFIG_PATH']=previous
        for process,stream in captures:
            process.terminate();process.wait(timeout=3);stream.close()
        for module in reversed(modules):
            try:pulse('unload-module',module)
            except Exception:pass
