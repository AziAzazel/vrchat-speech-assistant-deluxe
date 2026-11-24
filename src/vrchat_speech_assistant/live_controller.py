"""Qt-facing Studio controller; authenticated loopback IPC carries commands only."""
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from PySide6 import QtCore
from vrchat_speech_assistant.output_control import check_cancelled, playback_callback, OutputCancelled


def worker_command(flag, argument):
    prefix=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-m','vrchat_speech_assistant']
    return [*prefix,flag,str(argument)]


class StudioController(QtCore.QObject):
    status=QtCore.Signal(dict)
    devices=QtCore.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process=None;self.connection=None;self.listener=None;self.thread=None
        self.stopping=threading.Event();self.ready=threading.Event();self.commands=queue.Queue(128)
        self.folder=tempfile.TemporaryDirectory(prefix='deluxe-studio-')
        self.jobs={};self.jobs_lock=threading.Lock();self.settings=None;self.active=False
        self.probing=False;self.generation=0;self.error='';self.closed=False;self.expected_stop=False

    def refresh_devices(self):
        if self.probing:return
        self.probing=True
        def probe():
            try:
                with tempfile.TemporaryDirectory(prefix='deluxe-studio-probe-') as folder:
                    report=Path(folder)/'devices.json'
                    result=subprocess.run(worker_command('--live-voice-probe',report),stdin=subprocess.DEVNULL,
                                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=25,
                                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    if result.returncode:raise RuntimeError('Probe failed')
                    devices=json.loads(report.read_text(encoding='utf-8'))
                    if not isinstance(devices,list):raise ValueError('Invalid probe')
                    if not self.closed:self.devices.emit(devices)
            except Exception:
                if not self.closed:self.status.emit({'type':'error','message':'Audio scan failed. Reconnect your devices and click Refresh.'})
            finally:self.probing=False
        threading.Thread(target=probe,daemon=True).start()

    def send(self, message):
        try:self.commands.put_nowait(message);return True
        except queue.Full:
            self.status.emit({'type':'error','message':'Studio is busy. Wait for the engine to respond.'});return False

    def start(self, settings):
        if self.active:return
        if self.process is not None:self.stop()
        self.settings=settings;self.stopping.clear();self.ready.clear();self.active=True;self.expected_stop=False
        self.generation+=1;generation=self.generation
        self.commands=queue.Queue(128)
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(.25)
        self.listener=listener;token=secrets.token_urlsafe(32)
        environment=dict(os.environ,DELUXE_STUDIO_SESSION=token,DELUXE_STUDIO_TEMP=self.folder.name)
        try:
            self.process=subprocess.Popen(worker_command('--live-voice-worker',listener.getsockname()[1]),env=environment,
                                          stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except Exception:
            listener.close();self.active=False;raise
        def communicate():
            connection=None
            try:
                deadline=time.monotonic()+15
                while not self.stopping.is_set() and time.monotonic()<deadline:
                    try:connection,_=listener.accept();break
                    except socket.timeout:
                        if self.process.poll() is not None:raise RuntimeError('Audio worker exited during startup.')
                if connection is None:raise TimeoutError('Audio worker did not connect.')
                connection.settimeout(.01);pending=b'';authenticated=False
                self.connection=connection
                while not self.stopping.is_set() and generation==self.generation:
                    try:
                        chunk=connection.recv(65536)
                        if not chunk:raise RuntimeError('Audio worker exited.')
                        pending+=chunk
                        if len(pending)>2*1024*1024:raise ValueError('Invalid audio worker response.')
                        while b'\n' in pending:
                            line,pending=pending.split(b'\n',1);message=json.loads(line)
                            if not authenticated:
                                if message.get('type')!='hello' or not secrets.compare_digest(message.get('token',''),token):raise ValueError('Invalid worker session.')
                                authenticated=True
                                connection.sendall(json.dumps({'type':'configure','settings':self.settings}).encode()+b'\n')
                            elif message.get('type')=='tts_done':
                                with self.jobs_lock:
                                    job=self.jobs.get(message.get('id'))
                                    if job:job['cancelled']=message.get('cancelled',False);job['event'].set()
                            else:
                                if message.get('type')=='ready':self.ready.set()
                                if message.get('type')=='reconnecting':self.ready.clear()
                                self.status.emit(message)
                    except socket.timeout:pass
                    if authenticated:
                        while not self.commands.empty():
                            try:message=self.commands.get_nowait()
                            except queue.Empty:break
                            connection.sendall(json.dumps(message,allow_nan=False).encode()+b'\n')
            except Exception as error:
                if not self.stopping.is_set() and not self.expected_stop and generation==self.generation:
                    self.active=False;self.ready.clear()
                    self.status.emit({'type':'crashed','message':'Studio audio worker stopped ('+type(error).__name__+'). Your other app features remain available. Switch ON to reconnect.'})
            finally:
                self.ready.clear()
                if connection:connection.close()
                listener.close()
                with self.jobs_lock:
                    for job in self.jobs.values():job['cancelled']=True;job['event'].set()
        self.thread=threading.Thread(target=communicate,daemon=True);self.thread.start()

    def configure(self, settings):
        self.settings=settings
        if self.active:self.send({'type':'configure','settings':settings})

    def route_tts(self, path):
        # Called only inside a speech output worker. Files are copied before the
        # provider's temporary directory goes away; IPC never touches Qt widgets.
        if not self.active or not self.settings or self.settings['source'] not in ('TTS','Both'):return False
        if not self.ready.is_set():raise RuntimeError('Start Studio and wait for its audio devices before routing TTS.')
        identifier=uuid.uuid4().hex
        suffix=Path(path).suffix.lower()
        if suffix not in ('.wav','.ogg','.mp3'):return False
        target=Path(self.folder.name)/(identifier+suffix)
        shutil.copyfile(path,target)
        job={'event':threading.Event(),'cancelled':False}
        with self.jobs_lock:self.jobs[identifier]=job
        try:
            if not self.send({'type':'tts','path':str(target),'id':identifier}):raise RuntimeError('Studio queue is full.')
            import soundfile as sf
            callback=playback_callback();duration=sf.info(str(path)).duration;started=time.monotonic()
            if callback:callback(0,duration)
            deadline=time.monotonic()+330
            while not job['event'].wait(.03):
                try:check_cancelled()
                except OutputCancelled:self.send({'type':'cancel','id':identifier});raise
                if time.monotonic()>deadline:raise TimeoutError('Studio TTS timed out.')
                if callback:callback(min(duration,time.monotonic()-started),duration)
            if job['cancelled']:raise OutputCancelled()
            return True
        finally:
            with self.jobs_lock:self.jobs.pop(identifier,None)
            target.unlink(missing_ok=True)

    def stop(self):
        self.expected_stop=True
        if self.process is not None:
            self.send({'type':'stop'})
            # Let the communication thread flush stop, then isolate a hung driver.
            try:self.process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait(timeout=2)
        self.stopping.set();self.ready.clear();self.active=False
        if self.thread:self.thread.join(timeout=.5)
        if self.listener:
            try:self.listener.close()
            except OSError:pass
        self.process=None

    def close(self):
        self.closed=True
        self.stop()
        # A pending asynchronous probe may still refer to QObject signals; it
        # has a strict subprocess timeout and never owns any audio device here.
        self.folder.cleanup()
