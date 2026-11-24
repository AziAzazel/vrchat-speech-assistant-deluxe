"""Measured DSP behavior and Studio integration, without cloud credentials."""
from copy import deepcopy
import json
import threading
from unittest.mock import Mock
import numpy as np
import pytest

from vrchat_speech_assistant.live_settings import default_patch, builtin_presets, validate_patch, atomic_json, read_json
from vrchat_speech_assistant.live_dsp import VoicePipeline, detect_pitch, nearest_note
from vrchat_speech_assistant.live_worker import guard_route, find_device
from vrchat_speech_assistant.output_control import audio_delivery_scope, audio_delivery_callback


def tone(frequency=220, seconds=.8, rate=48000):
    t=np.arange(round(seconds*rate))/rate
    return .1*np.sin(2*np.pi*frequency*t)


def natural():
    patch=default_patch();patch['effects']['gate']['enabled']=False
    return patch


def render(patch, samples, rate=48000, mode='Low Latency', block=256):
    engine=VoicePipeline(rate,mode,patch)
    result=np.concatenate([engine.process(samples[i:i+block]) for i in range(0,len(samples),block)])
    return result,engine


def frequency(x, rate=48000):
    if x.ndim==2:x=x[:,0]
    x=x[len(x)//3:2*len(x)//3]
    return np.argmax(abs(np.fft.rfft(x*np.hanning(len(x)))))*rate/len(x)


@pytest.mark.parametrize('rate',[44100,48000])
@pytest.mark.parametrize('f0',[80,120,220,450,800])
def test_yin_finds_fundamental_and_rejects_noise(rate,f0):
    x=tone(f0,4096/rate,rate)
    detected,confidence=detect_pitch(x,rate)
    assert detected==pytest.approx(f0,rel=.005) and confidence>.9
    assert detect_pitch(np.zeros(4096),rate)[0] is None
    assert detect_pitch(np.random.default_rng(4).normal(0,.1,4096),rate)[0] is None


@pytest.mark.parametrize('shift',[-12,-7,7,12])
def test_streaming_pitch_changes_frequency_not_frame_count(shift):
    patch=natural();patch['effects']['pitch'].update(enabled=True,semitones=shift)
    source=tone(seconds=1.2);result,engine=render(patch,source)
    assert len(result)==len(source)
    assert frequency(result)==pytest.approx(220*2**(shift/12),abs=4)
    assert np.isfinite(result).all() and abs(result).max()<.9
    assert engine.metrics['algorithm_ms']==pytest.approx(1024/48000*1000)


def test_formant_moves_spectral_envelope_without_moving_f0():
    rate=48000;t=np.arange(rate)/rate;source=np.zeros_like(t)
    for harmonic in range(1,50):
        f=120*harmonic
        amplitude=np.exp(-.5*((f-600)/100)**2)+.6*np.exp(-.5*((f-1440)/160)**2)+(.2 if harmonic==1 else 0)
        source+=amplitude*np.sin(2*np.pi*f*t)
    source=source/abs(source).max()*.2
    outputs=[]
    for formant in (0,5):
        patch=natural();patch['effects']['pitch'].update(enabled=True,formant=formant)
        output,_=render(patch,source);outputs.append(output[:,0])
        f0,confidence=detect_pitch(output[-4096:,0],rate)
        assert f0==pytest.approx(120,abs=1) and confidence>.9
    def centroid(x):
        x=x[len(x)//3:2*len(x)//3];power=abs(np.fft.rfft(x*np.hanning(len(x))))**2
        frequencies=np.fft.rfftfreq(len(x),1/rate);mask=(frequencies>250)&(frequencies<1100)
        return sum(frequencies[mask]*power[mask])/sum(power[mask])
    assert centroid(outputs[1])>centroid(outputs[0])+50


def test_hard_tune_quantizes_to_allowed_note_and_skips_unvoiced_noise():
    patch=natural();patch['effects']['tune'].update(enabled=True,strength=100,retune=0,smoothing=0)
    patch['hard_tune']=True
    output,engine=render(patch,tone(450,1.2))
    assert frequency(output)==pytest.approx(440,abs=4)
    assert engine.metrics['input_note']=='A4' and engine.metrics['target_note']=='A4'
    noise=np.random.default_rng(18).normal(0,.03,24000)
    _,engine=render(patch,noise)
    assert engine.metrics['f0'] is None and engine.metrics['target_note']=='—'
    patch['scale']='Custom';patch['notes']=[0];patch['key']='D'
    assert nearest_note(60.1,patch)==62


@pytest.mark.parametrize('name',list(builtin_presets()))
def test_every_preset_is_valid_and_produces_finite_bounded_audio(name):
    patch=builtin_presets()[name];assert validate_patch(patch)==patch
    output,engine=render(patch,tone(seconds=.3))
    assert np.isfinite(output).all() and abs(output).max()<=10**(-1/20)+1e-6
    assert np.sqrt(np.mean(output**2))>1e-5
    if name in ('Vocaloid','Miku Inspired','Robot'):
        assert engine.metrics['algorithm_ms']==pytest.approx(1024/48000*1000) # fused FFT chain


@pytest.mark.parametrize('effect',['input_gain','gate','reduction','vocoder','harmonizer','vibrato','chorus',
                                    'distortion','bitcrusher','glitch','reverb','delay','eq','compressor','output_gain'])
def test_each_exposed_effect_changes_real_samples(effect):
    patch=natural();patch['effects'][effect]['enabled']=True
    updates={'input_gain':{'db':6},'gate':{'threshold':-10},'reduction':{'amount':100},
             'vocoder':{'mix':100},'distortion':{'amount':80},'eq':{'low':-12},'output_gain':{'db':-12},
             'compressor':{'threshold':-40,'ratio':10}}
    patch['effects'][effect].update(updates.get(effect,{}))
    source=tone(seconds=.6);baseline,_=render(natural(),source);actual,_=render(patch,source)
    assert np.mean((actual-baseline)**2)>1e-8,effect


def test_live_update_bypass_panic_and_limiter_are_real_and_do_not_restart_engine():
    patch=natural();engine=VoicePipeline(patch=patch);source=tone(seconds=.1)
    for _ in range(8):engine.process(source)
    patch['effects']['pitch'].update(enabled=True,semitones=12)
    engine.update(patch);result=engine.process(source)
    assert engine.revision==1 and np.isfinite(result).all()
    bypassed=engine.process(source,bypass=True)
    np.testing.assert_allclose(bypassed[256:,0],source[256:],atol=1e-6) # 5 ms anti-click transition
    assert not engine.process(source,panic=True).any()
    limited=engine.process(np.ones(256)*20,bypass=True)
    assert abs(limited).max()<1 and engine.metrics['clipping']


def test_harmonizer_independent_voice_pan_changes_stereo_energy():
    patch=natural();patch['effects']['harmonizer']['enabled']=True
    for i,voice in enumerate(patch['voices']):voice.update(enabled=i==0,pitch=7,pan=-1,db=0)
    output,_=render(patch,tone(seconds=1))
    assert np.sqrt(np.mean(output[:,0]**2))>np.sqrt(np.mean(output[:,1]**2))*1.05


@pytest.mark.parametrize('mutation',[lambda p:p['effects']['pitch'].update(formant=13),
    lambda p:p['effects']['delay'].update(feedback=100),lambda p:p.update(notes=[]),
    lambda p:p.update(order=['pitch']*18),lambda p:p['effects']['input_gain'].update(db=float('nan'))])
def test_unsafe_presets_are_rejected(mutation):
    patch=default_patch();mutation(patch)
    with pytest.raises(ValueError):validate_patch(patch)


def test_json_roundtrip_and_audio_loop_protection(tmp_path):
    path=tmp_path/'preset.json';patch=builtin_presets()['Vocaloid']
    atomic_json(path,{'version':1,'name':'Vocaloid copy','patch':patch})
    assert validate_patch(read_json(path)['patch'])==patch
    mic={'key':'mic','name':'USB microphone','inputs':1,'outputs':0}
    out={'key':'out','name':'CABLE Input','inputs':0,'outputs':2}
    guard_route(mic,out)
    with pytest.raises(ValueError):guard_route(dict(mic,name='CABLE Output'),out)
    with pytest.raises(ValueError):guard_route(mic,out,out)
    with pytest.raises(ValueError):find_device([mic],'missing','inputs')


def test_tts_delivery_scope_is_thread_local_and_does_not_replace_other_playback():
    callback=Mock(return_value=True)
    with audio_delivery_scope(callback):
        assert audio_delivery_callback() is callback
        seen=[];thread=threading.Thread(target=lambda:seen.append(audio_delivery_callback()));thread.start();thread.join()
        assert seen==[None]
    assert audio_delivery_callback() is None


@pytest.mark.parametrize('rate',[44100,48000])
@pytest.mark.parametrize('block',[64,128,256,512,1024,2048])
def test_streaming_formats_and_buffer_sizes_preserve_frame_counts(rate,block):
    patch=natural();patch['effects']['pitch'].update(enabled=True,semitones=4,formant=1)
    source=tone(seconds=.4,rate=rate)
    output,engine=render(patch,source,rate=rate,block=block)
    assert output.shape==(len(source),2) and np.isfinite(output).all()
    assert np.sqrt(np.mean(output**2))>.001


@pytest.mark.parametrize('physically_held',[False,True])
def test_windows_ptt_releases_when_key_is_up_or_hotkey_worker_stops(monkeypatch,physically_held):
    import ctypes
    from types import SimpleNamespace
    from vrchat_speech_assistant import hotkeys
    class API:
        delivered=False
        def PeekMessageW(self,pointer,window,first,last,remove):
            if first==0x0312 and not self.delivered:
                pointer._obj.wParam=1;self.delivered=True;return 1
            return 0
        def RegisterHotKey(self,*args):return True
        def UnregisterHotKey(self,*args):return True
        def GetAsyncKeyState(self,key):return 0x8000 if physically_held else 0
    api=API();monkeypatch.setattr(hotkeys,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setattr(hotkeys,'ctypes',SimpleNamespace(windll=SimpleNamespace(user32=api),byref=ctypes.byref))
    actions=[];worker=hotkeys.GlobalHotkeys({'studio_ptt':'Ctrl+F6'},actions.append,lambda text:None)
    calls=iter((False,True));worker.stop_event=SimpleNamespace(wait=lambda timeout:next(calls))
    worker._run()
    assert actions==['studio_ptt','studio_ptt_release']


def test_intentional_worker_stop_is_not_reported_as_a_crash(monkeypatch):
    import socket
    import time
    from PySide6 import QtCore
    from vrchat_speech_assistant import live_controller
    class Worker:
        def __init__(self,argv,**kwargs):
            self.ended=threading.Event()
            port=int(argv[-1]);token=kwargs['env']['DELUXE_STUDIO_SESSION']
            def run():
                connection=socket.create_connection(('127.0.0.1',port),timeout=3)
                connection.sendall(json.dumps({'type':'hello','token':token}).encode()+b'\n')
                reader=connection.makefile('rb')
                reader.readline() # initial validated configuration
                connection.sendall(json.dumps({'type':'ready','rate':48000,'buffer':256}).encode()+b'\n')
                while True:
                    line=reader.readline()
                    if not line or json.loads(line).get('type')=='stop':break
                reader.close();connection.close()
                # A normal process can close IPC before native cleanup finishes.
                time.sleep(.15);self.ended.set()
            self.thread=threading.Thread(target=run,daemon=True);self.thread.start()
        def poll(self):return 0 if self.ended.is_set() else None
        def wait(self,timeout=None):
            if not self.ended.wait(timeout):raise live_controller.subprocess.TimeoutExpired('test worker',timeout)
            return 0
        def kill(self):self.ended.set()
    monkeypatch.setattr(live_controller.subprocess,'Popen',Worker)
    controller=live_controller.StudioController();events=[]
    controller.status.connect(events.append,QtCore.Qt.DirectConnection)
    try:
        controller.start({'source':'TTS'})
        assert controller.ready.wait(3)
        controller.stop()
        assert not any(event['type']=='crashed' for event in events)
    finally:controller.close()
