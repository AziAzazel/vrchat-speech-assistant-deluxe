"""Validated, versioned offline Studio presets; no audio or credentials in JSON."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile

# name: parameter -> (default, minimum, maximum, step). Shared by DSP and UI.
PARAMETERS = {
    'input_gain': {'db': (0, -24, 24, .5)},
    'gate': {'threshold': (-55, -90, 0, 1), 'attack': (5, .1, 100, 1), 'release': (100, 5, 1000, 5)},
    'reduction': {'amount': (0, 0, 100, 1)},
    'tune': {'strength': (0, 0, 100, 1), 'retune': (80, 0, 150, 1), 'humanize': (0, 0, 100, 1), 'smoothing': (15, 0, 100, 1)},
    'pitch': {'semitones': (0, -12, 12, .1), 'formant': (0, -12, 12, .1)},
    'vocoder': {'mix': (0, 0, 100, 1), 'bands': (24, 8, 64, 1)},
    'harmonizer': {'mix': (50, 0, 100, 1)},
    'vibrato': {'depth': (.3, 0, 2, .05), 'rate': (5, .1, 12, .1)},
    'chorus': {'mix': (20, 0, 100, 1), 'depth': (4, .1, 15, .1), 'rate': (.8, .1, 8, .1)},
    'distortion': {'amount': (0, 0, 100, 1)},
    'bitcrusher': {'bits': (8, 2, 16, 1), 'rate': (8000, 1000, 48000, 100), 'mix': (50, 0, 100, 1)},
    'glitch': {'intensity': (20, 0, 100, 1), 'frequency': (3, .1, 20, .1)},
    'reverb': {'mix': (15, 0, 100, 1), 'decay': (1.2, .1, 5, .1)},
    'delay': {'mix': (20, 0, 100, 1), 'time': (220, 1, 1000, 1), 'feedback': (25, 0, 85, 1)},
    'eq': {'low': (0, -18, 18, .5), 'mid': (0, -18, 18, .5), 'high': (0, -18, 18, .5)},
    'compressor': {'threshold': (-18, -60, 0, 1), 'ratio': (4, 1, 20, .5), 'attack': (5, .1, 100, 1), 'release': (100, 5, 1000, 5)},
    'output_gain': {'db': (0, -24, 24, .5)},
    'limiter': {'ceiling': (-1, -12, 0, .1)},
}
SCALES = {'Chromatic': tuple(range(12)), 'Major': (0,2,4,5,7,9,11), 'Minor': (0,2,3,5,7,8,10),
          'Pentatonic': (0,2,4,7,9), 'Harmonic Minor': (0,2,3,5,7,8,11), 'Custom': ()}
KEYS = ('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
MODES = {'Low Latency': 1024, 'Balanced': 2048, 'High Quality': 4096}
CARRIERS = ('Saw','Square','Synth','Noise')
HARMONIES = {'Octave Up': (12,), 'Octave Down': (-12,), 'Major Third': (4,), 'Minor Third': (3,),
             'Perfect Fifth': (7,), 'Major Chord': (4,7), 'Minor Chord': (3,7), 'Choir': (-12,0,7,12), 'Custom': ()}


def default_patch():
    effects = {name: dict(enabled=name in ('input_gain','gate','output_gain','limiter'),
                          **{key: value[0] for key,value in values.items()}) for name,values in PARAMETERS.items()}
    return {'version': 1, 'effects': effects, 'order': list(PARAMETERS), 'key': 'C', 'scale': 'Chromatic',
            'notes': list(range(12)), 'hard_tune': False, 'carrier': 'Saw', 'harmony': 'Major Chord',
            'voices': [{'enabled': i < 2, 'pitch': value, 'formant': 0, 'db': -9, 'pan': (-.4 if i%2==0 else .4),
                        'delay': 0, 'detune': 0} for i,value in enumerate((4,7,12,-12))]}


def validate_patch(value):
    if not isinstance(value, dict) or value.get('version') != 1:
        raise ValueError('Unsupported Studio preset version.')
    patch = default_patch()
    if set(value.get('effects', {})) != set(PARAMETERS):
        raise ValueError('Preset must contain the complete effect chain.')
    for name,spec in PARAMETERS.items():
        effect = value['effects'][name]
        if not isinstance(effect, dict) or type(effect.get('enabled')) is not bool:
            raise ValueError('Each effect needs an enabled flag.')
        for key,(_,low,high,_) in spec.items():
            number = effect.get(key)
            if type(number) not in (int,float) or not math.isfinite(number) or not low <= number <= high:
                raise ValueError(f'Invalid {name}: {key}.')
            if key in ('bands','bits') and int(number) != number:
                raise ValueError('Bands and bit depth must be whole numbers.')
        patch['effects'][name] = dict(effect)
    order = value.get('order')
    if not isinstance(order,list) or len(order) != len(PARAMETERS) or set(order) != set(PARAMETERS):
        raise ValueError('Each effect must appear exactly once in the chain.')
    patch['order'] = list(order)
    for key,choices in (('key',KEYS),('scale',SCALES),('carrier',CARRIERS),('harmony',HARMONIES)):
        if value.get(key) not in choices:
            raise ValueError('Unknown musical scale, key, carrier or harmony.')
        patch[key] = value[key]
    notes = value.get('notes')
    if not isinstance(notes,list) or not notes or len(notes)>12 or any(type(n) is not int or n not in range(12) for n in notes):
        raise ValueError('Select at least one allowed note.')
    patch['notes'] = sorted(set(notes))
    if type(value.get('hard_tune')) is not bool:
        raise ValueError('Invalid Hard Tune flag.')
    patch['hard_tune'] = value['hard_tune']
    voices = value.get('voices')
    if not isinstance(voices,list) or len(voices) != 4:
        raise ValueError('A preset needs four harmony voice slots.')
    limits = {'pitch':(-12,12),'formant':(-12,12),'db':(-48,0),'pan':(-1,1),'delay':(0,200),'detune':(-50,50)}
    for voice in voices:
        if not isinstance(voice,dict) or type(voice.get('enabled')) is not bool:
            raise ValueError('Invalid harmony voice.')
        for key,(low,high) in limits.items():
            n=voice.get(key)
            if type(n) not in (int,float) or not math.isfinite(n) or not low<=n<=high:
                raise ValueError('Invalid harmony voice parameter.')
    patch['voices'] = deepcopy(voices)
    return patch


def builtin_presets():
    values = [('Natural',0,0,0,80,0), ('Vocaloid',5,3,100,5,20), ('Anime Girl',7,4,15,60,0),
              ('Anime Boy',2,1,20,40,0), ('Teto Inspired',4,2,100,5,10), ('Miku Inspired',7,3,100,0,15),
              ('Cyberpunk',-3,-2,80,10,45), ('Robot',0,-3,100,0,100), ('Daft Punk Inspired',0,0,100,0,80),
              ('GLaDOS Inspired',0,-1,100,5,35), ('Demon',-7,-5,20,40,15), ('Chiptune',3,0,100,0,40),
              ('Broken Vocaloid',5,3,100,0,25), ('Harmonizer',0,0,100,10,10)]
    presets = {}
    for name,pitch,formant,tune,retune,vocoder in values:
        p=default_patch(); e=p['effects']
        e['pitch'].update(enabled=bool(pitch or formant),semitones=pitch,formant=formant)
        e['tune'].update(enabled=bool(tune),strength=tune,retune=retune)
        e['vocoder'].update(enabled=bool(vocoder),mix=vocoder)
        p['hard_tune']=retune==0
        if name in ('Harmonizer','Demon','GLaDOS Inspired'):
            e['harmonizer']['enabled']=True
            if name=='Demon':
                p['harmony']='Octave Down'
                for i,v in enumerate(p['voices']): v.update(enabled=i==0,pitch=-12)
            if name=='GLaDOS Inspired':
                p['harmony']='Custom';p['voices'][0].update(pitch=7,db=-15)
                for v in p['voices'][1:]: v['enabled']=False
        if name in ('Chiptune','Broken Vocaloid'):
            e['bitcrusher'].update(enabled=True,bits=6,mix=35);p['carrier']='Square'
        if name=='Broken Vocaloid': e['glitch'].update(enabled=True,intensity=40,frequency=4)
        if name=='Cyberpunk': e['distortion'].update(enabled=True,amount=30)
        if name!='Natural': e['output_gain']['db']=-6
        presets[name]=p
    return presets


def atomic_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.studio-',delete=False,mode='w',encoding='utf-8') as stream:
            temporary=Path(stream.name);json.dump(value,stream,ensure_ascii=False,allow_nan=False,indent=2)
        os.replace(temporary,path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def read_json(path):
    if Path(path).stat().st_size > 1024*1024:
        raise ValueError('Studio JSON must be smaller than 1 MB.')
    return json.loads(Path(path).read_text(encoding='utf-8'))
