"""PortAudio lives only in this subprocess; a driver crash cannot kill Qt.

Blocking PortAudio streams run on a dedicated thread, so no Python allocations,
locks or disk IO occur in audio callbacks (there are no Python callbacks).
"""
from collections import deque
import json
import os
from pathlib import Path
import queue
import socket
import threading
import time

import numpy as np
from vrchat_speech_assistant.live_settings import validate_patch


def device_snapshot(context):
    import pyaudio
    devices=[]
    for i in range(context.get_device_count()):
        d=context.get_device_info_by_index(i);host=context.get_host_api_info_by_index(d['hostApi'])['name']
        devices.append({'index':i,'name':d['name'],'host':host,'key':host+' | '+d['name'],
                        'inputs':int(d['maxInputChannels']),'outputs':int(d['maxOutputChannels'])})
    return devices


def find_device(devices, key, kind):
    found=[d for d in devices if d['key']==key and d[kind]>0]
    if len(found)!=1: raise ValueError('Selected device is disconnected or ambiguous. Choose it again after Refresh.')
    return found[0]


def guard_route(input_device, output_device, monitor_device=None):
    capture=input_device['name'].lower() if input_device else ''
    outputs=[d['name'].lower() for d in (output_device,monitor_device) if d]
    if any(word in capture for word in ('stereo mix','what u hear','.monitor')):
        raise ValueError('Choose a physical microphone, not a playback/monitor capture source.')
    if 'cable' in capture and any('cable' in name for name in outputs):
        raise ValueError('The selected virtual cable feeds its output back into its input. Choose your real microphone.')
    if monitor_device and monitor_device['key']==output_device['key']:
        raise ValueError('Monitor and VRChat output must be different devices to avoid duplicate audio.')


class AudioWorker:
    def __init__(self, connection, folder):
        self.connection,self.folder=connection,Path(folder).resolve()
        self.stop=threading.Event();self.panic=threading.Event();self.ptt=threading.Event()
        self.settings=None;self.version=0;self.clips=queue.Queue(2);self.replays=queue.Queue(1);self.decode_jobs=queue.Queue(2)
        self.events=queue.Queue(100);self.recording=None;self.record_blocks=[];self.record_count=0
        self.cancelled=set();self.active_id=None

    def emit(self, kind, **values):
        try:self.events.put_nowait(dict(type=kind,**values))
        except queue.Full:pass

    def path(self, value):
        path=Path(value).resolve()
        if path.parent!=self.folder or path.suffix.lower() not in ('.wav','.ogg','.mp3'):
            raise ValueError('Invalid Studio session file.')
        return path

    def control(self, message):
        kind=message.get('type')
        if kind=='configure':
            config=message['settings'];config['patch']=validate_patch(config['patch'])
            if config['rate'] not in (44100,48000) or config['buffer'] not in (64,128,256,512,1024,2048):raise ValueError('Unsupported audio format.')
            if config['source'] not in ('Microphone','TTS','Both'):raise ValueError('Unsupported source.')
            self.settings=config;self.version+=1
        elif kind=='stop':self.stop.set()
        elif kind=='panic':
            self.panic.set()
            if self.active_id:self.cancelled.add(self.active_id)
            while not self.clips.empty():
                try:
                    clip=self.clips.get_nowait();self.emit('tts_done',id=clip[0],cancelled=True)
                except queue.Empty:break
        elif kind=='resume':self.panic.clear()
        elif kind=='ptt':self.ptt.set() if message.get('pressed') else self.ptt.clear()
        elif kind=='cancel':self.cancelled.add(message['id'])
        elif kind in ('tts','replay'):
            if kind=='tts' and self.panic.is_set():
                self.emit('tts_done',id=message['id'],cancelled=True);return
            self.path(message['path'])
            self.decode_jobs.put_nowait(message)
        elif kind=='record':
            if message.get('enabled'):
                self.recording=self.path(message['path']);self.record_blocks=[];self.record_count=0
            else:self.finish_recording()

    def finish_recording(self):
        if self.recording is None:return
        path=self.recording;blocks=self.record_blocks;rate=self.settings['rate']
        self.recording=None;self.record_blocks=[]
        def write():
            import soundfile as sf
            try:
                if blocks:sf.write(str(path),np.concatenate(blocks),rate,subtype='PCM_16');self.emit('recorded',path=str(path))
            except Exception:self.emit('error',message='The test recording could not be written.')
        threading.Thread(target=write,daemon=True).start()

    def decoding(self):
        import math
        import soundfile as sf
        from scipy.signal import resample_poly
        while not self.stop.is_set():
            try:message=self.decode_jobs.get(timeout=.1)
            except queue.Empty:continue
            path=None
            try:
                path=self.path(message['path']);kind=message['type'];identifier=message.get('id')
                if path.stat().st_size>32*1024*1024:raise ValueError('Clip exceeds 32 MB.')
                info=sf.info(str(path))
                if info.duration>300:raise ValueError('Clip exceeds five minutes.')
                data,rate=sf.read(str(path),dtype='float32',always_2d=True)
                if rate!=self.settings['rate']:
                    factor=math.gcd(rate,self.settings['rate'])
                    data=resample_poly(data,self.settings['rate']//factor,rate//factor,axis=0).astype(np.float32)
                if kind=='tts':
                    if self.panic.is_set() or identifier in self.cancelled:self.emit('tts_done',id=identifier,cancelled=True)
                    else:self.clips.put_nowait((identifier,data.mean(axis=1)))
                else:self.replays.put_nowait(data)
            except Exception:
                if message.get('id'):self.emit('tts_done',id=message['id'],cancelled=True)
                self.emit('error',message='Clip could not be decoded or the Studio queue is full (32 MB / five minutes maximum).')
            finally:
                if path is not None:path.unlink(missing_ok=True)

    def audio(self):
        import pyaudio
        from vrchat_speech_assistant.live_dsp import VoicePipeline
        while not self.stop.is_set():
            if self.settings is None:self.stop.wait(.05);continue
            context=None;capture=None;output=None;monitor=None;monitor_thread=None
            monitor_stop=threading.Event();monitor_queue=queue.Queue(3)
            try:
                config=self.settings;structural=tuple(config.get(k) for k in ('input','output','monitor_device','rate','buffer','mode','channels','source'))
                rate,block=config['rate'],config['buffer']
                context=pyaudio.PyAudio();devices=device_snapshot(context)
                input_device=find_device(devices,config['input'],'inputs') if config['source']!='TTS' else None
                output_device=find_device(devices,config['output'],'outputs')
                monitor_device=None;monitor_error=None
                if config.get('monitor_device'):
                    try:monitor_device=find_device(devices,config['monitor_device'],'outputs')
                    except ValueError:monitor_error='Monitor unavailable; VRChat output continues. Stop and Refresh devices to restore monitoring.'
                guard_route(input_device,output_device,monitor_device)
                output_channels=min(2,output_device['outputs'])
                if input_device:
                    capture_channels=min(2,input_device['inputs'])
                    capture=context.open(format=pyaudio.paFloat32,channels=capture_channels,rate=rate,input=True,
                                         input_device_index=input_device['index'],frames_per_buffer=block)
                output=context.open(format=pyaudio.paFloat32,channels=output_channels,rate=rate,output=True,
                                    output_device_index=output_device['index'],frames_per_buffer=block)
                if monitor_device:
                    monitor_channels=min(2,monitor_device['outputs'])
                    try:
                        monitor=context.open(format=pyaudio.paFloat32,channels=monitor_channels,rate=rate,output=True,
                                             output_device_index=monitor_device['index'],frames_per_buffer=block)
                    except Exception:
                        monitor_error='Monitor could not open; VRChat output continues. Stop and check the monitor format/device.'
                    def monitoring(stream=monitor, stop_flag=monitor_stop, messages=monitor_queue):
                        try:
                            while not stop_flag.is_set():
                                try:data=messages.get(timeout=.1)
                                except queue.Empty:continue
                                stream.write(data,exception_on_underflow=False)
                        except Exception:self.emit('error',message='Monitoring device was disconnected; select it again.')
                    if monitor is not None:
                        monitor_thread=threading.Thread(target=monitoring,daemon=True);monitor_thread.start()
                pipeline=VoicePipeline(rate,config['mode'],config['patch']);revision=self.version
                clip=None;clip_position=0;clip_tail=None;replay=None;replay_position=0;last_status=0.;overruns=0;feedback_frames=0;was_panic=False;clipped=False
                self.emit('ready',rate=rate,buffer=block)
                if monitor_error:self.emit('error',message=monitor_error)
                while not self.stop.is_set():
                    current=self.settings
                    if structural!=tuple(current.get(k) for k in ('input','output','monitor_device','rate','buffer','mode','channels','source')):break
                    updated=time.perf_counter()
                    if revision!=self.version:pipeline.update(current['patch']);revision=self.version
                    update_ms=(time.perf_counter()-updated)*1000
                    if capture:
                        raw=capture.read(block,exception_on_overflow=False)
                        if len(raw)!=block*capture_channels*4:raise OSError('Microphone stream ended.')
                        microphone=np.frombuffer(raw,dtype=np.float32).reshape(-1,capture_channels).mean(axis=1)
                    else:microphone=np.zeros(block,dtype=np.float32)
                    mic_level=float(np.max(np.abs(microphone)))
                    if current.get('mute') or (current.get('ptt') and not self.ptt.is_set()):microphone.fill(0)
                    if current.get('activation') and np.sqrt(np.mean(microphone**2))<10**(current.get('activation_db',-45)/20):microphone.fill(0)
                    x=microphone.copy()
                    if clip is None:
                        try:
                            identifier,data=self.clips.get_nowait();clip=(identifier,data);clip_position=0;clip_tail=None;self.active_id=identifier
                        except queue.Empty:pass
                    if clip is not None:
                        identifier,data=clip
                        if identifier in self.cancelled:
                            self.cancelled.discard(identifier);self.emit('tts_done',id=identifier,cancelled=True);clip=None;self.active_id=None
                        else:
                            part=data[clip_position:clip_position+block];x[:len(part)]+=part;clip_position+=len(part)
                    panic_active=self.panic.is_set()
                    if panic_active!=was_panic:
                        pipeline=VoicePipeline(rate,current['mode'],current['patch']);was_panic=panic_active
                    if panic_active:x.fill(0)
                    processed=pipeline.process(x,bypass=current.get('bypass',False),panic=panic_active)
                    pipeline.metrics['dsp_ms']+=update_ms
                    pipeline.metrics['load']=pipeline.metrics['dsp_ms']/(block/rate*1000)*100
                    clipped |= pipeline.metrics['clipping']
                    feedback_frames=feedback_frames+block if pipeline.metrics['input_level']>.9 and pipeline.metrics['clipping'] else 0
                    if feedback_frames>rate*.75 and not self.panic.is_set():
                        self.panic.set();processed.fill(0)
                        self.emit('error',message='Sustained input/output clipping: possible feedback. Studio output muted; check routing before Resume.')
                    output_data=processed.mean(axis=1) if config['channels']==1 or output_channels==1 else processed
                    if output_channels==2 and output_data.ndim==1:output_data=np.repeat(output_data[:,None],2,axis=1)
                    output.write(np.ascontiguousarray(output_data,dtype=np.float32).tobytes(),exception_on_underflow=False)
                    if clip is not None and clip_position>=len(clip[1]):
                        if clip_tail is None:
                            clip_tail=int((pipeline.metrics['algorithm_ms']/1000+output.get_output_latency())*rate)+block
                        else:clip_tail-=block
                        if clip_tail<=0:self.emit('tts_done',id=clip[0],cancelled=False);clip=None;self.active_id=None
                    if self.recording is not None:
                        self.record_blocks.append(processed.copy());self.record_count+=block
                        if self.record_count>=rate*10:self.finish_recording()
                    if monitor is not None:
                        audible=processed.copy() if current.get('monitor') else np.zeros_like(processed)
                        if replay is None:
                            try:replay=self.replays.get_nowait();replay_position=0
                            except queue.Empty:pass
                        if replay is not None:
                            part=replay[replay_position:replay_position+block]
                            if part.shape[1]==1:part=np.repeat(part,2,axis=1)
                            audible[:len(part)]+=part[:,:2];replay_position+=len(part)
                            if replay_position>=len(replay):replay=None
                        if self.panic.is_set():audible.fill(0)
                        audible=np.clip(audible,-.89,.89)
                        if monitor_channels==1:audible=audible.mean(axis=1)
                        try:monitor_queue.put_nowait(np.ascontiguousarray(audible,dtype=np.float32).tobytes())
                        except queue.Full:
                            try:monitor_queue.get_nowait()
                            except queue.Empty:pass
                    now=time.monotonic()
                    if pipeline.metrics['load']>100:overruns+=1
                    if now-last_status>.1:
                        last_status=now
                        values=dict(pipeline.metrics,overruns=overruns)
                        values.update(clipping=clipped,mic_level=mic_level);clipped=False
                        values['latency_ms']=values['algorithm_ms']+block/rate*1000+(capture.get_input_latency()*1000 if capture else 0)+output.get_output_latency()*1000
                        self.emit('meters',**values)
            except Exception as error:
                self.emit('reconnecting',message=f'Audio device unavailable ({type(error).__name__}). Retrying the same saved devices; no automatic rerouting.')
                if self.active_id:self.emit('tts_done',id=self.active_id,cancelled=True);self.active_id=None
                self.stop.wait(1)
            finally:
                monitor_stop.set()
                if monitor_thread:monitor_thread.join(timeout=1)
                for stream in (capture,output,monitor):
                    if stream:
                        try:stream.stop_stream();stream.close()
                        except Exception:pass
                if context:
                    try:context.terminate()
                    except Exception:pass
        self.finish_recording()

    def run(self):
        threading.Thread(target=self.decoding,daemon=True).start()
        audio=threading.Thread(target=self.audio,daemon=True);audio.start()
        self.connection.settimeout(.01);pending=b''
        try:
            while not self.stop.is_set():
                try:
                    chunk=self.connection.recv(65536)
                    if not chunk:break
                    pending+=chunk
                    if len(pending)>2*1024*1024:raise ValueError('Command too large.')
                    while b'\n' in pending:
                        line,pending=pending.split(b'\n',1)
                        message=json.loads(line)
                        try:self.control(message)
                        except Exception as error:
                            if message.get('id'):self.emit('tts_done',id=message['id'],cancelled=True)
                            self.emit('error',message='Invalid Studio command: '+type(error).__name__)
                except socket.timeout:pass
                while not self.events.empty():
                    try:message=self.events.get_nowait()
                    except queue.Empty:break
                    self.connection.sendall(json.dumps(message,allow_nan=False).encode()+b'\n')
        finally:
            self.stop.set();audio.join(timeout=2);self.connection.close()


def main(argv):
    if argv[0]=='--live-voice-probe':
        import pyaudio
        context=pyaudio.PyAudio()
        try:Path(argv[1]).write_text(json.dumps(device_snapshot(context)),encoding='utf-8')
        finally:context.terminate()
        return 0
    connection=socket.create_connection(('127.0.0.1',int(argv[1])),timeout=10)
    connection.sendall(json.dumps({'type':'hello','token':os.environ['DELUXE_STUDIO_SESSION']}).encode()+b'\n')
    AudioWorker(connection,os.environ['DELUXE_STUDIO_TEMP']).run()
    return 0
