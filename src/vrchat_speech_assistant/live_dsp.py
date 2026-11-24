"""Stateful offline voice DSP. Runs in an isolated audio worker, never in Qt.

FFT pitch/formant stages use overlap/add and continuous phase, not playback-rate
changes. Disabled modules are skipped. Public block boundaries permit atomic
parameter snapshots; output gain ramps suppress switching discontinuities.
"""
import math
import time
import numpy as np
from scipy import signal
from vrchat_speech_assistant.live_settings import validate_patch, SCALES, KEYS, MODES


def note_name(midi):
    if midi is None: return '—'
    note=int(round(midi));return f'{KEYS[note%12]}{note//12-1}'


def nearest_note(midi, patch):
    root=KEYS.index(patch['key'])
    notes=patch['notes'] if patch['scale']=='Custom' else SCALES[patch['scale']]
    allowed={(root+n)%12 for n in notes}
    candidates=[n for n in range(math.floor(midi)-12,math.ceil(midi)+13) if n%12 in allowed]
    return min(candidates,key=lambda n:(abs(n-midi),n))


def detect_pitch(samples, rate):
    """FFT-accelerated YIN difference + cumulative normalization and confidence."""
    x=np.asarray(samples,dtype=np.float64);x=x-x.mean()
    if len(x)<128 or np.sqrt(np.mean(x*x)) < 1e-4: return None,0.
    n=len(x);maximum=min(n//2,int(rate/65));minimum=max(2,int(rate/1100))
    power=np.concatenate(([0.],np.cumsum(x*x)))
    fft=np.fft.rfft(x,n=2*n)
    correlation=np.fft.irfft(fft*fft.conj(),n=2*n)[:maximum+1]
    lags=np.arange(maximum+1)
    difference=np.maximum(0,power[n-lags]+power[n]-power[lags]-2*correlation)
    cumulative=np.cumsum(difference[1:])
    normalized=np.ones(maximum+1)
    normalized[1:]=difference[1:]*np.arange(1,maximum+1)/np.maximum(cumulative,1e-15)
    lag=minimum
    while lag<maximum-1:
        if normalized[lag]<.15:
            while lag+1<maximum and normalized[lag+1]<normalized[lag]: lag+=1
            break
        lag+=1
    else: return None,0.
    confidence=float(1-normalized[lag])
    if confidence<.8: return None,confidence
    left,center,right=normalized[lag-1:lag+2]
    denominator=left-2*center+right
    offset=.5*(left-right)/denominator if abs(denominator)>1e-12 else 0
    return float(rate/(lag+np.clip(offset,-.5,.5))),confidence


class Delay:
    def __init__(self, rate, seconds=2):
        self.buffer=np.zeros((int(rate*seconds)+4096,2));self.position=0

    def process(self, x, delay, feedback=0):
        x=np.asarray(x);mono=x.ndim==1
        stereo=np.repeat(x[:,None],2,axis=1) if mono else x
        delay=max(1,min(len(self.buffer)-4096,int(delay)))
        out=np.empty_like(stereo)
        # Segmenting at the tap distance makes short feedback delays causal.
        for start in range(0,len(x),delay):
            size=min(delay,len(x)-start);idx=(self.position+np.arange(size))%len(self.buffer)
            read=(idx-delay)%len(self.buffer);wet=self.buffer[read].copy()
            out[start:start+size]=wet
            self.buffer[idx]=stereo[start:start+size]+np.clip(feedback,-.98,.98)*wet
            self.position=(self.position+size)%len(self.buffer)
        return out[:,0] if mono else out

    def modulate(self, x, delays):
        x=np.asarray(x);mono=x.ndim==1
        stereo=np.repeat(x[:,None],2,axis=1) if mono else x
        idx=(self.position+np.arange(len(x)))%len(self.buffer)
        self.buffer[idx]=stereo
        position=(idx-np.clip(delays,1,len(self.buffer)-4096))%len(self.buffer)
        base=np.floor(position).astype(int);part=(position-base)[:,None]
        out=self.buffer[base]*(1-part)+self.buffer[(base+1)%len(self.buffer)]*part
        self.position=(self.position+len(x))%len(self.buffer)
        return out[:,0] if mono else out


class SpectralVoice:
    def __init__(self, rate, size):
        self.rate,self.size,self.hop=rate,size,size//4
        self.window=np.hanning(size+1)[:-1]
        self.input=np.zeros(size);self.overlap=np.zeros(size);self.weight=np.zeros(size)
        self.pending=np.empty(0);self.output=np.zeros(self.hop)
        self.previous=np.zeros(size//2+1);self.phase=np.zeros(size//2+1)
        self.bins=np.arange(size//2+1);self.started=False;self.clock=0
        self.noise=None;self.rng=np.random.default_rng(1847)
        self.last_shift=0.

    def _hop(self, block, semitones, formant, reduction, vocoder):
        n,h=self.size,self.hop
        self.input[:-h]=self.input[h:];self.input[-h:]=block
        spectrum=np.fft.rfft(self.input*self.window);magnitude=np.abs(spectrum)
        angles=np.angle(spectrum)
        if not self.started: self.previous=angles.copy();self.phase=angles.copy();self.started=True
        if semitones or formant or self.last_shift:
            self.last_shift+=np.clip(semitones-self.last_shift,-1.,1.)
            factor=2**(self.last_shift/12);source=self.bins/factor
            advance=2*np.pi*h*self.bins/n
            delta=angles-self.previous-advance;delta-=2*np.pi*np.round(delta/(2*np.pi))
            frequency=self.bins+delta*n/(2*np.pi*h)
            shifted=np.interp(source,self.bins,magnitude,left=0,right=0)
            # Smooth cepstral envelope is independent of harmonic spacing.
            cepstrum=np.fft.irfft(np.log(np.maximum(magnitude,1e-8)),n=n)
            lifter=max(8,min(n//4,int(self.rate/800)))
            cepstrum[lifter:-lifter]=0
            envelope=np.exp(np.fft.rfft(cepstrum).real)
            target_envelope=np.interp(self.bins/2**(formant/12),self.bins,envelope,left=envelope[0],right=envelope[-1])
            old_envelope=np.interp(source,self.bins,envelope,left=envelope[0],right=envelope[-1])
            shifted*=np.clip(target_envelope/np.maximum(old_envelope,1e-8),.05,20)
            shifted*=np.clip(np.linalg.norm(magnitude)/max(np.linalg.norm(shifted),1e-8),.1,20)
            self.phase+=2*np.pi*h/n*np.interp(source,self.bins,frequency,right=0)*factor
            spectrum=shifted*np.exp(1j*self.phase)
        else:
            self.phase=angles.copy()
        self.previous=angles
        if reduction:
            # Slowly track a per-bin noise floor, falling quickly when quiet.
            if self.noise is None:self.noise=magnitude*.25
            self.noise=np.minimum(self.noise*1.002+1e-6,magnitude*.9+1e-7)
            gain=np.maximum(.03,1-reduction/100*self.noise/np.maximum(magnitude,1e-8))
            spectrum*=gain
        if vocoder:
            mix,bands,carrier,f0=vocoder
            t=(np.arange(n)+self.clock)/self.rate
            phase=2*np.pi*f0*t
            if carrier=='Saw': wave=signal.sawtooth(phase)
            elif carrier=='Square': wave=signal.square(phase)
            elif carrier=='Synth': wave=np.sin(phase)+.5*np.sin(phase*2)+.25*np.sin(phase*3)
            else: wave=self.rng.normal(0,.5,n)
            carrier_spectrum=np.fft.rfft(wave*self.window)
            edges=np.unique(np.clip(np.geomspace(60,self.rate*.46,int(bands)+1)*n/self.rate,1,n//2).astype(int))
            shaped=np.zeros_like(spectrum)
            for low,high in zip(edges[:-1],edges[1:]):
                energy=np.sqrt(np.mean(np.abs(spectrum[low:high])**2))
                power=np.sqrt(np.mean(np.abs(carrier_spectrum[low:high])**2))
                shaped[low:high]=carrier_spectrum[low:high]*min(30,energy/max(power,1e-8))
            spectrum=(1-mix/100)*spectrum+mix/100*shaped
        self.clock+=h
        self.overlap+=np.fft.irfft(spectrum,n=n)*self.window
        self.weight+=self.window**2
        # A shifted spectrum can contain energy where the startup window was
        # almost zero. Never amplify that by dividing by a tiny edge weight.
        result=self.overlap[:h]/np.maximum(self.weight[:h],1.)
        self.overlap[:-h]=self.overlap[h:];self.overlap[-h:]=0
        self.weight[:-h]=self.weight[h:];self.weight[-h:]=0
        return result

    def process(self, x, semitones=0, formant=0, reduction=0, vocoder=None):
        self.pending=np.concatenate((self.pending,x));chunks=[self.output]
        while len(self.pending)>=self.hop:
            block=self.pending[:self.hop];self.pending=self.pending[self.hop:]
            chunks.append(self._hop(block,semitones,formant,reduction,vocoder))
        result=np.concatenate(chunks);output=result[:len(x)].copy();self.output=result[len(x):]
        return output


class VoicePipeline:
    def __init__(self, rate=48000, mode='Balanced', patch=None):
        from vrchat_speech_assistant.live_settings import default_patch
        self.rate,self.size=rate,MODES[mode]
        self.patch=validate_patch(patch or default_patch())
        self.spectral={name:SpectralVoice(rate,self.size) for name in ('pitch','tune','reduction','vocoder','h0','h1','h2','h3')}
        self.delays={name:Delay(rate) for name in ('delay','chorus','vibrato','h0','h1','h2','h3','h_dry','r0','r1','r2','r3')}
        self.history=np.zeros(4096);self.tune_history=np.zeros(2048);self.f0=None;self.target=None;self.confidence=0.
        self.smoothed=None;self.correction=0.;self.clock=0;self.gate=0.;self.compression=1.
        self.gains={'input_gain':1.,'output_gain':1.};self.last=0.;self.changed=False
        self.harmony_gains=np.ones(4)
        self.rng=np.random.default_rng(235);self.glitch_hold=np.zeros(2048);self.crush_last=0.;self.crush_phase=0
        self.glitch_rate=1.;self.glitch_offset=0
        self.low=signal.butter(2,250,fs=rate,output='sos');self.high=signal.butter(2,3500,fs=rate,btype='high',output='sos')
        self.eq_state=None
        self.metrics={};self.revision=0
        self.was_bypassed=False

    def update(self, patch):
        patch=validate_patch(patch)
        if patch!=self.patch:
            old=self.patch
            for name in ('input_gain','output_gain'):
                if patch['effects'][name]['enabled'] and not old['effects'][name]['enabled']:self.gains[name]=1.
            if patch['effects']['glitch']['enabled'] and not old['effects']['glitch']['enabled']:
                self.glitch_hold=np.resize(self.history[-2048:],2048)
            if patch['effects']['bitcrusher']['enabled']!=old['effects']['bitcrusher']['enabled']:
                self.crush_last=0.;self.crush_phase=0
            for name,keys in (('delay',('delay',)),('chorus',('chorus',)),('vibrato',('vibrato',)),
                              ('reverb',('r0','r1','r2','r3'))):
                if patch['effects'][name]['enabled']!=old['effects'][name]['enabled']:
                    for key in keys:self.delays[key]=Delay(self.rate)
            for name in ('pitch','tune','reduction','vocoder'):
                if patch['effects'][name]['enabled'] and not old['effects'][name]['enabled']:
                    voice=SpectralVoice(self.rate,self.size);p=patch['effects'][name]
                    shift=p.get('semitones',0);formant=p.get('formant',0);vocoder=None
                    if name=='tune' and self.f0:
                        midi=69+12*np.log2(self.f0/440);shift=(nearest_note(midi,patch)-midi)*p['strength']/100
                    if name=='vocoder':vocoder=(p['mix'],p['bands'],patch['carrier'],self.f0 or 110)
                    voice.process(self.history,shift,formant,p.get('amount',0),vocoder)
                    self.spectral[name]=voice
                    self.spectral.pop(name+'_right',None)
            if patch['effects']['harmonizer']['enabled']:
                if not old['effects']['harmonizer']['enabled']:
                    self.delays['h_dry'].process(self.history,self.size)
                for i,settings in enumerate(patch['voices']):
                    if settings['enabled'] and (not old['effects']['harmonizer']['enabled'] or not old['voices'][i]['enabled']):
                        voice=SpectralVoice(self.rate,self.size)
                        warm=voice.process(self.history,settings['pitch']+settings['detune']/100,settings['formant'])
                        self.spectral['h'+str(i)]=voice
                        self.delays['h'+str(i)]=Delay(self.rate)
                        if settings['delay']:self.delays['h'+str(i)].process(warm,settings['delay']*.001*self.rate)
            self.patch=patch;self.changed=True;self.revision+=1

    @staticmethod
    def mono(x): return x.mean(axis=1) if x.ndim==2 else x

    def spectral_audio(self, name, x, *args, **kwargs):
        if x.ndim==1:return self.spectral[name].process(x,*args,**kwargs)
        right=name+'_right'
        if right not in self.spectral:
            self.spectral[right]=SpectralVoice(self.rate,self.size)
            self.spectral[right].process(self.history,*args,**kwargs)
        return np.column_stack((self.spectral[name].process(x[:,0],*args,**kwargs),
                                self.spectral[right].process(x[:,1],*args,**kwargs)))

    def tuning(self, x, p):
        self.tune_history=np.concatenate((self.tune_history,self.mono(x)))[-2048:]
        f0,_=detect_pitch(self.tune_history,self.rate)
        correction=0.
        if f0:
            midi=69+12*np.log2(f0/440)
            smoothing=math.exp(-len(x)/(self.rate*max(.00001,p['smoothing']*.0015))) if p['smoothing'] else 0
            self.smoothed=midi if self.smoothed is None else self.smoothed*smoothing+midi*(1-smoothing)
            self.target=nearest_note(self.smoothed,self.patch)
            correction=(self.target-self.smoothed)*p['strength']/100*(1-p['humanize']/100)
        milliseconds=0 if self.patch['hard_tune'] else p['retune']
        alpha=0 if not milliseconds else np.exp(-len(x)/(self.rate*milliseconds*.001))
        self.correction=self.correction*alpha+correction*(1-alpha)
        return self.correction if f0 else 0.

    def _envelope(self, x, threshold, attack, release, compress=False, ratio=4):
        level=np.max(np.abs(x),axis=1) if x.ndim==2 else np.abs(x);out=np.empty(len(x))
        value=self.compression if compress else self.gate
        for i,sample in enumerate(level):
            if compress:
                db=20*np.log10(max(sample,1e-8));target=10**(min(0,(threshold+(db-threshold)/ratio)-db)/20) if db>threshold else 1
                rising=target<value
            else: target=float(sample>10**(threshold/20));rising=target>value
            coefficient=math.exp(-1/(self.rate*(attack if rising else release)*.001))
            value=target+(value-target)*coefficient;out[i]=value
        if compress:self.compression=value
        else:self.gate=value
        return x*out[:,None] if x.ndim==2 else x*out

    def _effect(self, name, x, p):
        n=len(x);mono=self.mono(x)
        if name in self.gains:
            target=10**(p['db']/20);ramp=np.linspace(self.gains[name],target,n)
            self.gains[name]=target
            return x*ramp[:,None] if x.ndim==2 else x*ramp
        if name=='gate':return self._envelope(x,p['threshold'],p['attack'],p['release'])
        if name=='compressor':return self._envelope(x,p['threshold'],p['attack'],p['release'],True,p['ratio'])
        if name=='limiter':
            ceiling=10**(p['ceiling']/20)
            self._limited |= bool(np.any(np.abs(x)>ceiling))
            return np.clip(x,-ceiling,ceiling)
        if name=='reduction':return self.spectral_audio(name,x,reduction=p['amount'])
        if name=='pitch':return self.spectral_audio(name,x,p['semitones'],p['formant'])
        if name=='tune':
            return self.spectral_audio(name,x,self.tuning(mono,p))
        if name=='vocoder':
            frequency=440*2**((self.target-69)/12) if self.target is not None else (self.f0 or 110)
            return self.spectral_audio(name,x,vocoder=(p['mix'],p['bands'],self.patch['carrier'],frequency))
        if name=='harmonizer':
            dry=self.delays['h_dry'].process(mono,self.size)
            stereo=np.repeat(dry[:,None],2,axis=1)
            for i,voice in enumerate(self.patch['voices']):
                if not voice['enabled']: continue
                wet=self.spectral['h'+str(i)].process(mono,voice['pitch']+voice['detune']/100,voice['formant'])
                reference=np.sqrt(np.mean(dry*dry));level=np.sqrt(np.mean(wet*wet))
                gain=float(np.clip(reference/max(level,1e-6),.25,8))
                self.harmony_gains[i]=self.harmony_gains[i]*.95+gain*.05
                wet*=self.harmony_gains[i]
                if voice['delay']:wet=self.delays['h'+str(i)].process(wet,voice['delay']*.001*self.rate)
                pan=(voice['pan']+1)*np.pi/4
                stereo+=wet[:,None]*np.array([np.cos(pan),np.sin(pan)])*10**(voice['db']/20)*p['mix']/100
            return stereo
        if name in ('chorus','vibrato'):
            time_axis=(self.clock+np.arange(n))/self.rate
            if name=='vibrato':
                # Delay derivative modulates frequency, with depth in semitones.
                depth=(2**(p['depth']/12)-1)/(2*np.pi*p['rate'])*self.rate
                taps=depth+2+depth*np.sin(2*np.pi*p['rate']*time_axis)
                return self.delays[name].modulate(x,taps)
            taps=self.rate*.012+self.rate*p['depth']*.001*np.sin(2*np.pi*p['rate']*time_axis)
            wet=self.delays[name].modulate(x,taps)
            return x*(1-p['mix']/100)+wet*p['mix']/100
        if name=='distortion':
            if not p['amount']:return x
            drive=1+p['amount']/5
            return np.tanh(x*drive)/np.tanh(drive)
        if name=='bitcrusher':
            stride=max(1,int(self.rate/p['rate']));idx=np.arange(n)+self.crush_phase
            held=np.empty_like(x);last=self.crush_last
            if x.ndim==1 and np.ndim(last):last=float(np.mean(last))
            if x.ndim==2 and not np.ndim(last):last=np.full(x.shape[1],last)
            for i,value in enumerate(x):
                if idx[i]%stride==0:last=value
                held[i]=last
            self.crush_phase=(self.crush_phase+n)%stride;self.crush_last=last
            levels=2**(int(p['bits'])-1);wet=np.round(held*levels)/levels
            return x*(1-p['mix']/100)+wet*p['mix']/100
        if name=='glitch':
            interval=max(1,int(self.rate/p['frequency']))
            if (self.clock//interval)!=(self.clock+n)//interval:
                self.glitch_hold=np.resize(x[::-1],(2048,2) if x.ndim==2 else 2048)
                self.glitch_rate=float(self.rng.choice((.5,1.,2.)));self.glitch_offset=int(self.rng.integers(0,2048))
            offset=(self.clock+np.arange(n))%2048
            mix=p['intensity']/100
            if x.ndim==2 and self.glitch_hold.ndim==1:self.glitch_hold=np.repeat(self.glitch_hold[:,None],2,axis=1)
            if x.ndim==1 and self.glitch_hold.ndim==2:self.glitch_hold=self.glitch_hold.mean(axis=1)
            # Octave-like sample repetition/reversal; no time added/removed.
            wet=self.glitch_hold[(offset*self.glitch_rate+self.glitch_offset).astype(int)%2048]
            return x*(1-mix)+wet*mix
        if name=='delay':
            wet=self.delays[name].process(x,p['time']*.001*self.rate,p['feedback']/100)
            return x*(1-p['mix']/100)+wet*p['mix']/100
        if name=='reverb':
            wet=np.zeros_like(x)
            for i,seconds in enumerate((.029,.037,.041,.053)):
                feedback=min(.98,10**(-3*seconds/p['decay']))
                wet+=self.delays['r'+str(i)].process(x,seconds*self.rate,feedback)*.25
            return x*(1-p['mix']/100)+wet*p['mix']/100
        if name=='eq':
            data=x[:,None] if x.ndim==1 else x
            if self.eq_state is None or self.eq_state[0].shape[-1]!=data.shape[1]:
                self.eq_state=[np.zeros((len(self.low),2,data.shape[1])),np.zeros((len(self.high),2,data.shape[1]))]
            low,self.eq_state[0]=signal.sosfilt(self.low,data,axis=0,zi=self.eq_state[0])
            high,self.eq_state[1]=signal.sosfilt(self.high,data,axis=0,zi=self.eq_state[1])
            result=low*10**(p['low']/20)+(data-low-high)*10**(p['mid']/20)+high*10**(p['high']/20)
            return result[:,0] if x.ndim==1 else result
        return x

    def process(self, samples, bypass=False, panic=False):
        started=time.perf_counter();x=np.asarray(samples,dtype=np.float64)
        x=self.mono(x);x=np.nan_to_num(x,nan=0,posinf=0,neginf=0)
        peak_in=float(np.max(np.abs(x))) if len(x) else 0
        self._limited=False
        self.history=np.concatenate((self.history,x))[-max(4096,self.size*2):]
        self.f0,self.confidence=detect_pitch(self.history[-2048:],self.rate)
        self.target=None
        if bypass!=self.was_bypassed:
            if not bypass:
                # Disabled FFT/delay stages must not replay old syllables when
                # leaving bypass. Re-seed them from the current input history.
                saved=self.patch
                self.patch=dict(saved,effects={name:dict(p,enabled=False) for name,p in saved['effects'].items()})
                self.update(saved)
            self.was_bypassed=bypass;self.changed=True
        spectral_stages=0
        if not bypass:
            active=[name for name in self.patch['order'] if self.patch['effects'][name]['enabled']]
            index=0
            while index<len(active):
                name=active[index];index+=1
                parameters=self.patch['effects'][name]
                # Adjacent tune -> pitch -> vocoder share one FFT and one
                # latency window. A user-reordered tune after pitch stays a
                # separate stage and detects the already-shifted signal.
                group=[name]
                if name in ('tune','pitch'):
                    if name=='tune' and index<len(active) and active[index]=='pitch':group.append('pitch');index+=1
                    if index<len(active) and active[index]=='vocoder':group.append('vocoder');index+=1
                if len(group)>1:
                    shift=self.tuning(x,self.patch['effects']['tune']) if 'tune' in group else 0
                    formant=0;vocoder=None
                    if 'pitch' in group:
                        p=self.patch['effects']['pitch'];shift+=p['semitones'];formant=p['formant']
                    if 'vocoder' in group:
                        p=self.patch['effects']['vocoder'];f0=440*2**((self.target-69)/12) if self.target is not None else (self.f0 or 110)
                        vocoder=(p['mix'],p['bands'],self.patch['carrier'],f0)
                    x=self.spectral_audio(name,x,shift,formant,vocoder=vocoder)
                    spectral_stages+=1
                else:
                    x=self._effect(name,x,parameters)
                    if name in ('pitch','tune','reduction','vocoder','harmonizer'):spectral_stages+=1
        if x.ndim==1:x=np.repeat(x[:,None],2,axis=1)
        if self.changed and len(x):
            fade=np.linspace(0,1,min(len(x),int(.005*self.rate)))[:,None]
            x[:len(fade)]=self.last*(1-fade)+x[:len(fade)]*fade
            self.changed=False
        limiter=self.patch['effects']['limiter']
        ceiling=10**(limiter['ceiling']/20) if limiter['enabled'] and not bypass else .989
        clipped=self._limited or bool(np.any(np.abs(x)>ceiling))
        x=np.clip(np.nan_to_num(x),-ceiling,ceiling)
        if panic:x.fill(0)
        self.last=float(x[-1].mean()) if len(x) else 0
        self.clock+=len(x)
        spectral_latency=spectral_stages*self.size/self.rate*1000
        elapsed=(time.perf_counter()-started)*1000
        self.metrics={'input_level':peak_in,'output_level':float(np.max(np.abs(x))), 'clipping':clipped,
                      'f0':self.f0,'confidence':self.confidence,'input_note':note_name(69+12*np.log2(self.f0/440)) if self.f0 else '—',
                      'target_note':note_name(self.target),'dsp_ms':elapsed,'algorithm_ms':spectral_latency,
                      'load':elapsed/(len(x)/self.rate*1000)*100 if len(x) else 0,
                      'pitch_window_ms':2048/self.rate*1000,
                      'waveform':x[::max(1,len(x)//64),0].tolist(),'revision':self.revision}
        return x.astype(np.float32)
