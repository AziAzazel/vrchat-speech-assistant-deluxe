"""Live Voice Studio controls: every enabled control feeds the offline DSP."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import uuid
from PySide6 import QtCore, QtGui, QtWidgets
from vrchat_speech_assistant.diagnostics import DATA_DIR
from vrchat_speech_assistant.live_controller import StudioController
from vrchat_speech_assistant.live_settings import (PARAMETERS, KEYS, SCALES, MODES, CARRIERS, HARMONIES,
                                                  default_patch, builtin_presets, validate_patch, atomic_json, read_json)
from vrchat_speech_assistant.workspace_ui import form_group
from vrchat_speech_assistant.wheel_controls import NoWheelComboBox, NoWheelSlider


class Waveform(QtWidgets.QWidget):
    def __init__(self):
        super().__init__();self.values=[];self.setMinimumHeight(65)

    def paintEvent(self, event):
        painter=QtGui.QPainter(self);painter.fillRect(self.rect(),QtGui.QColor('#141414'))
        painter.setPen(QtGui.QColor('#64b5f6'));middle=self.height()/2
        if len(self.values)>1:
            path=QtGui.QPainterPath()
            for i,value in enumerate(self.values):
                point=QtCore.QPointF(i*self.width()/(len(self.values)-1),middle-value*middle*.9)
                if i:path.lineTo(point)
                else:path.moveTo(point)
            painter.drawPath(path)


class StudioParameter(QtWidgets.QWidget):
    changed=QtCore.Signal(float)

    def __init__(self, spec):
        super().__init__();default,low,high,step=spec;self.low,self.step=low,step
        layout=QtWidgets.QHBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.slider=NoWheelSlider(QtCore.Qt.Horizontal);self.slider.setRange(0,round((high-low)/step))
        self.number=QtWidgets.QDoubleSpinBox();self.number.setRange(low,high);self.number.setSingleStep(step)
        self.number.setDecimals(2 if step<.1 else 1 if step<1 else 0)
        layout.addWidget(self.slider,1);layout.addWidget(self.number)
        self.slider.valueChanged.connect(lambda value:self.number.setValue(low+value*step))
        self.number.valueChanged.connect(self._number);self.set_value(default)

    def _number(self, value):
        self.slider.blockSignals(True);self.slider.setValue(round((value-self.low)/self.step));self.slider.blockSignals(False)
        self.changed.emit(value)

    def set_value(self, value):
        self.number.blockSignals(True);self.number.setValue(value);self.number.blockSignals(False)
        self.slider.blockSignals(True);self.slider.setValue(round((value-self.low)/self.step));self.slider.blockSignals(False)


class LiveStudio(QtWidgets.QWidget):
    def __init__(self, window):
        super().__init__();self.window=window;self.loading=True;self.scanned=False
        self.path=DATA_DIR/'live-voice-studio.json';self.builtins=builtin_presets();self.device_list=[]
        self.store={'version':1,'presets':{},'favorites':[],'hotkeys':{},'selected':'b0','route':{}}
        self.patch=default_patch();self.selected='b0';self.recorded=None;self.ptt_held=False;self.persistence_blocked=False
        self.controller=StudioController(self);self.controller.status.connect(self.on_status);self.controller.devices.connect(self.on_devices)
        layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(12,10,12,10)
        self.notice=QtWidgets.QLabel('Offline DSP — microphone audio is processed directly. No speech recognition, AWS or Internet required.')
        self.notice.setWordWrap(True);layout.addWidget(self.notice)
        self.enabled=QtWidgets.QCheckBox('Live Voice Changer ON');self.enabled.toggled.connect(self.toggle)
        self.panic=QtWidgets.QPushButton('PANIC — mute all Studio output');self.panic.setStyleSheet('color:#ffaaaa;font-weight:bold;')
        self.panic.clicked.connect(lambda:self.action('studio_panic'))
        self.resume=QtWidgets.QPushButton('Resume output');self.resume.clicked.connect(lambda:self.controller.send({'type':'resume'}))
        row=QtWidgets.QHBoxLayout();row.addWidget(self.enabled);row.addWidget(self.panic);row.addWidget(self.resume);layout.addLayout(row)
        self.input,self.output,self.monitor_device,self.source,self.rate,self.buffer,self.mode,self.channels=[NoWheelComboBox() for _ in range(8)]
        self.source.addItems(('Microphone','TTS','Both'));self.rate.addItems(('48000','44100'))
        self.buffer.addItems(('64','128','256','512','1024','2048'));self.buffer.setCurrentText('256')
        self.mode.addItems(MODES);self.mode.setCurrentText('Balanced');self.channels.addItems(('Mono (VRChat)','Stereo'))
        self.monitor_device.addItem('None','');self.monitor=QtWidgets.QCheckBox('Monitor Voice (use headphones)')
        self.bypass=QtWidgets.QCheckBox('Bypass effects');self.mute=QtWidgets.QCheckBox('Mute microphone')
        self.ptt_mode=QtWidgets.QCheckBox('Push-to-Talk');self.activation=QtWidgets.QCheckBox('Voice Activation')
        self.activation_level=StudioParameter((-45,-70,-10,1))
        self.ptt_button=QtWidgets.QPushButton('Hold to talk');self.ptt_button.pressed.connect(lambda:self.set_ptt(True));self.ptt_button.released.connect(lambda:self.set_ptt(False))
        self.refresh=QtWidgets.QPushButton('Refresh audio devices');self.refresh.clicked.connect(self.controller.refresh_devices)
        layout.addWidget(form_group('Studio audio routing', [('Input microphone',self.input),('VRChat / cable output',self.output),
            ('Source',self.source),('',self.refresh)]))
        audio_options=QtWidgets.QToolButton();audio_options.setText('Audio format, monitoring & microphone controls');audio_options.setCheckable(True)
        layout.addWidget(audio_options)
        extra_audio=form_group('Audio options', [('Separate monitor device',self.monitor_device),('Sample rate (Hz)',self.rate),
            ('Buffer (samples)',self.buffer),('Performance',self.mode),('Output channels',self.channels),
            ('',self.monitor),('',self.bypass),('',self.mute),('',self.ptt_mode),('',self.ptt_button),
            ('',self.activation),('Activation threshold (dB)',self.activation_level)])
        layout.addWidget(extra_audio);extra_audio.hide();audio_options.toggled.connect(extra_audio.setVisible)
        self.route_controls=[self.input,self.output,self.monitor_device,self.source,self.rate,self.buffer,self.mode,self.channels]
        self.status=QtWidgets.QLabel('OFF — choose devices, then switch ON. Monitoring requires a different output device.')
        self.status.setWordWrap(True);layout.addWidget(self.status)
        monitoring_position=layout.count()
        self.preset=NoWheelComboBox();self.favorite=QtWidgets.QCheckBox('★ Favorite')
        preset_row=QtWidgets.QHBoxLayout();preset_row.addWidget(self.preset,1);preset_row.addWidget(self.favorite);layout.addLayout(preset_row)
        preset_buttons=QtWidgets.QHBoxLayout()
        for name,callback in [('Save',self.save_preset),('Save As…',self.save_as),('Duplicate',self.duplicate),
                              ('Delete',self.delete),('Reset',self.reset),('Import…',self.import_preset),('Export…',self.export_preset)]:
            button=QtWidgets.QPushButton(name);button.clicked.connect(callback);preset_buttons.addWidget(button)
        layout.addLayout(preset_buttons)
        self.preset_shortcut=QtWidgets.QLabel();shortcut_button=QtWidgets.QPushButton('Assign preset shortcut…')
        shortcut_button.clicked.connect(self.assign_shortcut)
        shortcut_row=QtWidgets.QHBoxLayout();shortcut_row.addWidget(self.preset_shortcut);shortcut_row.addWidget(shortcut_button);layout.addLayout(shortcut_row)
        label=QtWidgets.QLabel('Character-inspired names are DSP stylizations, not voice clones. Global Studio actions are configured in Roleplay → Shortcuts.')
        label.setWordWrap(True);layout.addWidget(label)
        self.effect_controls={};self.effect_enabled={}
        for name in ('pitch','tune','vocoder','harmonizer'):
            layout.addWidget(self.effect_group(name))
        self.key=NoWheelComboBox();self.key.addItems(KEYS);self.scale=NoWheelComboBox();self.scale.addItems(SCALES)
        self.hard=QtWidgets.QCheckBox('Hard Tune — immediate correction (overrides Retune Speed)')
        self.carrier=NoWheelComboBox();self.carrier.addItems(CARRIERS)
        self.harmony=NoWheelComboBox();self.harmony.addItems(HARMONIES)
        self.notes=QtWidgets.QWidget();note_row=QtWidgets.QHBoxLayout(self.notes);note_row.setContentsMargins(0,0,0,0)
        self.note_checks=[]
        for index,note in enumerate(KEYS):
            checkbox=QtWidgets.QCheckBox(note);checkbox.setChecked(True);checkbox.toggled.connect(self.notes_changed)
            self.note_checks.append(checkbox);note_row.addWidget(checkbox)
        layout.addWidget(form_group('Musical correction & carrier', [('Key',self.key),('Scale',self.scale),
            ('Custom allowed notes',self.notes),('',self.hard),('Vocoder carrier',self.carrier),('Harmony mode',self.harmony)]))
        self.voices=QtWidgets.QTableWidget(4,7)
        self.voices.setHorizontalHeaderLabels(('On','Pitch (st)','Formant (st)','Level (dB)','Pan','Delay (ms)','Detune (cents)'))
        self.voices.setMinimumHeight(180);self.voices.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        limits=[('pitch',-12,12,.1),('formant',-12,12,.1),('db',-48,0,.5),('pan',-1,1,.1),('delay',0,200,1),('detune',-50,50,1)]
        for index in range(4):
            checkbox=QtWidgets.QCheckBox();checkbox.toggled.connect(lambda value,i=index:self.voice_changed(i,'enabled',value));self.voices.setCellWidget(index,0,checkbox)
            for column,(name,low,high,step) in enumerate(limits,1):
                control=QtWidgets.QDoubleSpinBox();control.setRange(low,high);control.setSingleStep(step);control.setDecimals(1)
                control.valueChanged.connect(lambda value,i=index,k=name:self.voice_changed(i,k,value));self.voices.setCellWidget(index,column,control)
        layout.addWidget(form_group('Four independent harmony voices', [('',self.voices)]))
        self.advanced=QtWidgets.QToolButton();self.advanced.setText('Advanced Effects & processing order');self.advanced.setCheckable(True)
        layout.addWidget(self.advanced);advanced=QtWidgets.QWidget();advanced_layout=QtWidgets.QVBoxLayout(advanced)
        self.advanced_sections={}
        for name in PARAMETERS:
            if name not in ('pitch','tune','vocoder','harmonizer'):
                toggle=QtWidgets.QToolButton();toggle.setText(name.replace('_',' ').title());toggle.setCheckable(True)
                toggle.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon);toggle.setArrowType(QtCore.Qt.RightArrow)
                group=self.effect_group(name);advanced_layout.addWidget(toggle);advanced_layout.addWidget(group);group.hide()
                toggle.toggled.connect(group.setVisible)
                toggle.toggled.connect(lambda checked,button=toggle:button.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow))
                self.advanced_sections[name]=toggle
        self.order=QtWidgets.QListWidget();self.order.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.order.setMinimumHeight(180)
        advanced_layout.addWidget(QtWidgets.QLabel('Drag effects to reorder. The final safety ceiling is always enforced.'))
        advanced_layout.addWidget(self.order);layout.addWidget(advanced);advanced.hide();self.advanced.toggled.connect(advanced.setVisible)
        self.input_meter=QtWidgets.QProgressBar();self.output_meter=QtWidgets.QProgressBar()
        for meter in (self.input_meter,self.output_meter):meter.setRange(0,100)
        self.metrics=QtWidgets.QLabel('Microphone idle | F0: — | Input note: — | Target: — | DSP: — | Latency: — | Load: —')
        self.metrics.setWordWrap(True);self.clipping=QtWidgets.QLabel('No clipping');self.wave=Waveform()
        layout.insertWidget(monitoring_position,form_group('Live monitoring', [('Input level',self.input_meter),('Output level',self.output_meter),
                              ('',self.metrics),('',self.clipping),('',self.wave)]))
        record_row=QtWidgets.QHBoxLayout()
        self.record=QtWidgets.QPushButton('Test Recording (max 10 s)');self.record.setCheckable(True);self.record.toggled.connect(self.record_toggle)
        self.replay=QtWidgets.QPushButton('Listen to test');self.replay.clicked.connect(self.replay_recording);self.replay.setEnabled(False)
        self.export_record=QtWidgets.QPushButton('Save test WAV…');self.export_record.clicked.connect(self.save_recording);self.export_record.setEnabled(False)
        for button in (self.record,self.replay,self.export_record):record_row.addWidget(button)
        layout.addLayout(record_row)
        unavailable=QtWidgets.QLabel('Unavailable in this DSP release: AI/RVC model conversion, AMD DirectML and VST3 hosting. No models, plugins or cloud services are loaded.')
        unavailable.setWordWrap(True);unavailable.setEnabled(False);layout.addWidget(unavailable);layout.addStretch()
        self.apply_timer=QtCore.QTimer(self);self.apply_timer.setSingleShot(True);self.apply_timer.setInterval(30);self.apply_timer.timeout.connect(self.apply)
        self.save_timer=QtCore.QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.setInterval(500);self.save_timer.timeout.connect(self.persist)
        for combo in self.route_controls:combo.currentIndexChanged.connect(self.changed)
        for checkbox in (self.monitor,self.bypass,self.mute,self.ptt_mode,self.activation):checkbox.toggled.connect(self.changed)
        self.activation_level.changed.connect(self.changed)
        for combo in (self.key,self.scale,self.carrier):combo.currentTextChanged.connect(self.musical_changed)
        self.hard.toggled.connect(self.musical_changed);self.harmony.currentTextChanged.connect(self.harmony_changed)
        self.order.model().rowsMoved.connect(self.order_changed)
        self.favorite.toggled.connect(self.favorite_changed);self.preset.currentIndexChanged.connect(self.select_preset)
        self.load();self.loading=False
        QtWidgets.QApplication.instance().installEventFilter(self)

    def effect_group(self, name):
        title={'tune':'Auto-Tune','pitch':'Pitch / independent formant','eq':'Equalizer'}.get(name,name.replace('_',' ').title())
        enabled=QtWidgets.QCheckBox('Enable '+title);self.effect_enabled[name]=enabled
        rows=[('',enabled)]
        units={'semitones':'Semitones','formant':'Formant (semitones)','db':'Gain (dB)','threshold':'Threshold (dB)',
               'attack':'Attack (ms)','release':'Release (ms)','retune':'Retune speed (ms)','smoothing':'Pitch smoothing (%)',
               'strength':'Strength (%)','humanize':'Humanize (%)','time':'Time (ms)','feedback':'Feedback (%)','ceiling':'Ceiling (dBFS)'}
        for key,spec in PARAMETERS[name].items():
            control=StudioParameter(spec);self.effect_controls[name,key]=control
            control.changed.connect(lambda value,n=name,k=key:self.parameter_changed(n,k,value))
            label=units.get(key,key.title())
            if key in ('mix','amount','intensity'):label=key.title()+' (%)'
            if key in ('rate','frequency'):label=key.title()+' (Hz)'
            if key=='bits':label='Bit depth'
            if key=='decay':label='Decay (seconds)'
            if key=='depth':label='Depth (semitones)' if name=='vibrato' else 'Depth (ms)'
            if name=='eq':label=key.title()+' (dB)'
            rows.append((label,control))
        enabled.toggled.connect(lambda value,n=name:self.module_changed(n,value))
        return form_group(title,rows)

    def items(self):
        items=[('b'+str(i),name,patch) for i,(name,patch) in enumerate(self.builtins.items())]
        items += [(key,value['name'],value['patch']) for key,value in self.store['presets'].items()]
        return sorted(items,key=lambda item:(item[0] not in self.store['favorites'],item[1]!='Natural',item[1]))

    def rebuild_presets(self):
        self.preset.blockSignals(True);self.preset.clear()
        for identifier,name,_ in self.items():self.preset.addItem(('★ ' if identifier in self.store['favorites'] else '')+name,identifier)
        index=self.preset.findData(self.selected);self.preset.setCurrentIndex(max(0,index));self.preset.blockSignals(False)

    def load(self):
        defaults=deepcopy(self.store)
        try:
            if self.path.exists():
                store=read_json(self.path)
                if store.get('version')!=1 or not isinstance(store.get('presets'),dict) or len(store['presets'])>128:raise ValueError('Invalid Studio settings.')
                for key,preset in store['presets'].items():
                    if not isinstance(key,str) or not isinstance(preset.get('name'),str) or len(preset['name'])>80:raise ValueError('Invalid preset name.')
                    preset['patch']=validate_patch(preset['patch'])
                favorites=store.get('favorites',[]);hotkeys=store.get('hotkeys',{});route=store.get('route',{})
                if not isinstance(favorites,list) or any(not isinstance(k,str) for k in favorites):raise ValueError('Invalid favorites.')
                if not isinstance(hotkeys,dict) or any(not isinstance(k,str) or not isinstance(v,str) or len(v)>80 for k,v in hotkeys.items()):raise ValueError('Invalid hotkeys.')
                if not isinstance(route,dict) or any(not isinstance(route.get(k,''),str) or len(route.get(k,''))>512 for k in ('input','output','monitor_device')):raise ValueError('Invalid audio route.')
                activation=route.get('activation_db',-45)
                if type(activation) not in (int,float) or not -70<=activation<=-10:raise ValueError('Invalid voice activation threshold.')
                if any(type(route.get(k,False)) is not bool for k in ('bypass','mute','monitor','ptt','activation')):raise ValueError('Invalid routing flag.')
                if not isinstance(store.get('selected','b0'),str):raise ValueError('Invalid selected preset.')
                self.store.update(store)
                if 'working_patch' in store:self.patch=validate_patch(store['working_patch'])
        except (OSError,ValueError,TypeError,KeyError):
            if self.path.exists():
                try:shutil.copyfile(self.path,self.path.with_name('live-voice-studio.invalid-'+uuid.uuid4().hex[:8]+'.json'))
                except OSError:self.persistence_blocked=True
            self.store=defaults;self.patch=default_patch()
            self.status.setText('Could not load Studio settings. The original file was preserved; defaults are active.')
        self.selected=self.store.get('selected','b0');self.rebuild_presets()
        if self.preset.findData(self.selected)<0:self.selected='b0';self.rebuild_presets()
        route=self.store.get('route',{})
        for key,control in (('source',self.source),('rate',self.rate),('buffer',self.buffer),('mode',self.mode)):
            control.setCurrentText(str(route.get(key,control.currentText())))
        self.channels.setCurrentIndex(1 if route.get('channels')==2 else 0)
        self.activation_level.set_value(route.get('activation_db',-45))
        for key,control in (('bypass',self.bypass),('mute',self.mute),('monitor',self.monitor),('ptt',self.ptt_mode),('activation',self.activation)):
            control.setChecked(bool(route.get(key,False)))
        self.load_controls()

    def load_controls(self):
        before=self.loading;self.loading=True
        for name,parameters in self.patch['effects'].items():
            self.effect_enabled[name].setChecked(parameters['enabled'])
            for key in PARAMETERS[name]:
                control=self.effect_controls[name,key];control.set_value(parameters[key]);control.setEnabled(parameters['enabled'])
            if name in self.advanced_sections:self.advanced_sections[name].setChecked(parameters['enabled'])
        for key,control in (('key',self.key),('scale',self.scale),('carrier',self.carrier),('harmony',self.harmony)):control.setCurrentText(self.patch[key])
        self.hard.setChecked(self.patch['hard_tune'])
        self.effect_controls['tune','retune'].setEnabled(self.patch['effects']['tune']['enabled'] and not self.patch['hard_tune'])
        self.voices.setEnabled(self.patch['effects']['harmonizer']['enabled'])
        root=KEYS.index(self.patch['key'])
        for i,checkbox in enumerate(self.note_checks):checkbox.setChecked(i in self.patch['notes']);checkbox.setText(KEYS[(i+root)%12])
        self.notes.setEnabled(self.patch['scale']=='Custom')
        for i,voice in enumerate(self.patch['voices']):
            self.voices.cellWidget(i,0).setChecked(voice['enabled'])
            for column,key in enumerate(('pitch','formant','db','pan','delay','detune'),1):self.voices.cellWidget(i,column).setValue(voice[key])
        self.order.clear()
        for name in self.patch['order']:
            item=QtWidgets.QListWidgetItem(name.replace('_',' ').title());item.setData(QtCore.Qt.UserRole,name);self.order.addItem(item)
        self.favorite.setChecked(self.selected in self.store['favorites'])
        self.preset_shortcut.setText('Preset shortcut: '+(self.store['hotkeys'].get(self.selected,'') or 'Not assigned'))
        self.loading=before

    def activate(self):
        if not self.scanned:
            self.scanned=True;self.status.setText('Scanning local audio devices…');self.controller.refresh_devices()

    def snapshot(self):
        return {'patch':deepcopy(self.patch),'input':self.input.currentData() or self.store.get('route',{}).get('input',''),
                'output':self.output.currentData() or self.store.get('route',{}).get('output',''),
                'monitor_device':self.monitor_device.currentData() or '', 'source':self.source.currentText(),
                'rate':int(self.rate.currentText()),'buffer':int(self.buffer.currentText()),'mode':self.mode.currentText(),
                'channels':1 if self.channels.currentIndex()==0 else 2,'monitor':self.monitor.isChecked(),
                'bypass':self.bypass.isChecked(),'mute':self.mute.isChecked(),'ptt':self.ptt_mode.isChecked(),
                'activation':self.activation.isChecked(),'activation_db':self.activation_level.number.value()}

    def persist(self):
        if self.persistence_blocked:
            self.status.setText('Could not preserve invalid Studio settings. Export your preset or fix settings folder permissions.');return
        self.store.update(selected=self.selected,working_patch=deepcopy(self.patch),route=self.snapshot())
        self.store['route'].pop('patch',None)
        try:atomic_json(self.path,self.store)
        except OSError:self.status.setText('Studio settings could not be saved. Check the settings folder permissions.')

    def changed(self, *args):
        if self.loading:return
        if not self.monitor_device.currentData():
            self.monitor.blockSignals(True);self.monitor.setChecked(False);self.monitor.blockSignals(False)
        self.monitor.setEnabled(bool(self.monitor_device.currentData()))
        self.replay.setEnabled(bool(self.recorded and self.monitor_device.currentData()))
        if not self.apply_timer.isActive():self.apply_timer.start()
        self.save_timer.start()

    def apply(self):
        try:self.patch=validate_patch(self.patch);self.controller.configure(self.snapshot())
        except ValueError as error:self.status.setText(str(error))

    def parameter_changed(self, name, key, value):
        if self.loading:return
        self.patch['effects'][name][key]=int(value) if key in ('bands','bits') else value;self.changed()

    def module_changed(self, name, value):
        if self.loading:return
        self.patch['effects'][name]['enabled']=value
        for key in PARAMETERS[name]:self.effect_controls[name,key].setEnabled(value)
        if name=='tune':self.effect_controls['tune','retune'].setEnabled(value and not self.hard.isChecked())
        if name=='harmonizer':self.voices.setEnabled(value)
        self.changed()

    def musical_changed(self, *args):
        if self.loading:return
        self.patch.update(key=self.key.currentText(),scale=self.scale.currentText(),carrier=self.carrier.currentText(),hard_tune=self.hard.isChecked())
        self.effect_controls['tune','retune'].setEnabled(self.patch['effects']['tune']['enabled'] and not self.hard.isChecked())
        root=KEYS.index(self.patch['key'])
        for i,checkbox in enumerate(self.note_checks):checkbox.setText(KEYS[(i+root)%12])
        self.notes.setEnabled(self.patch['scale']=='Custom');self.changed()

    def notes_changed(self):
        if self.loading:return
        notes=[i for i,c in enumerate(self.note_checks) if c.isChecked()]
        if not notes:
            self.note_checks[self.patch['notes'][0]].setChecked(True);return
        self.patch['notes']=notes;self.changed()

    def voice_changed(self, index, key, value):
        if self.loading:return
        self.patch['voices'][index][key]=value
        self.patch['harmony']='Custom';self.harmony.blockSignals(True);self.harmony.setCurrentText('Custom');self.harmony.blockSignals(False);self.changed()

    def harmony_changed(self, name):
        if self.loading:return
        self.patch['harmony']=name
        if name!='Custom':
            offsets=HARMONIES[name]
            for i,voice in enumerate(self.patch['voices']):voice.update(enabled=i<len(offsets),pitch=offsets[i] if i<len(offsets) else 0)
            self.load_controls()
        self.changed()

    def order_changed(self, *args):
        if not self.loading:self.patch['order']=[self.order.item(i).data(QtCore.Qt.UserRole) for i in range(self.order.count())];self.changed()

    def on_devices(self, devices):
        self.device_list=devices;route=self.store.get('route',{});self.loading=True
        for key,control,kind in (('input',self.input,'inputs'),('output',self.output,'outputs'),('monitor_device',self.monitor_device,'outputs')):
            previous=control.currentData() or route.get(key,'');control.clear()
            if key=='monitor_device':control.addItem('None','')
            else:control.addItem('Choose device…','')
            for device in devices:
                if device[kind]>0:control.addItem(device['key'],device['key'])
            index=control.findData(previous)
            if index>=0:control.setCurrentIndex(index)
            elif previous:control.addItem('Disconnected: '+previous,previous);control.setCurrentIndex(control.count()-1)
        self.loading=False
        self.monitor.setEnabled(bool(self.monitor_device.currentData()))

    def toggle(self, enabled):
        if enabled:
            try:
                from vrchat_speech_assistant.live_worker import find_device, guard_route
                config=self.snapshot()
                capture=find_device(self.device_list,config['input'],'inputs') if config['source']!='TTS' else None
                output=find_device(self.device_list,config['output'],'outputs')
                monitor=find_device(self.device_list,config['monitor_device'],'outputs') if config['monitor_device'] else None
                guard_route(capture,output,monitor)
                if self.monitor.isChecked() and monitor is None:raise ValueError('Choose a separate monitor device first.')
                self.controller.start(config);self.status.setText('Opening the selected audio devices…')
            except Exception as error:
                self.enabled.blockSignals(True);self.enabled.setChecked(False);self.enabled.blockSignals(False)
                self.status.setText(str(error));return
        else:self.controller.stop();self.status.setText('OFF');self.set_ptt(False)
        for control in self.route_controls:control.setEnabled(not enabled)
        self.persist()

    def on_status(self, message):
        kind=message.get('type')
        if kind=='meters':
            import math
            for key,meter in (('input_level',self.input_meter),('output_level',self.output_meter)):
                value=message.get(key,0);meter.setValue(round(max(0,min(100,(20*math.log10(max(value,1e-6))+60)/60*100))))
                meter.setFormat(f'{20*math.log10(max(value,1e-6)):.1f} dBFS')
            frequency=f"{message['f0']:.1f} Hz" if message.get('f0') else '—'
            activity='Mic active' if message.get('mic_level',0)>.002 else 'Mic idle'
            self.metrics.setText(f"{activity} | F0: {frequency} | Input: {message.get('input_note','—')} | Target: {message.get('target_note','—')} | "
                                 f"DSP: {message['dsp_ms']:.2f} ms | Reported total: {message['latency_ms']:.1f} ms | "
                                 f"Load: {message['load']:.0f}% | DSP overruns: {message.get('overruns',0)}")
            self.metrics.setToolTip('DSP time is measured per block. Total is algorithm delay + buffer + driver-reported latency, not a physical round-trip measurement.')
            self.wave.values=message.get('waveform',[]);self.wave.update()
            self.clipping.setText('CLIPPING — safety ceiling active' if message.get('clipping') else 'No clipping')
            self.clipping.setStyleSheet('color:#ffaaaa;' if message.get('clipping') else '')
        elif kind=='ready':self.status.setText(f"ON — {message['rate']} Hz, {message['buffer']} samples. Local audio worker is running.")
        elif kind=='recorded':
            self.recorded=Path(message['path']);self.record.blockSignals(True);self.record.setChecked(False);self.record.blockSignals(False)
            self.replay.setEnabled(bool(self.monitor_device.currentData()));self.export_record.setEnabled(True)
        elif kind in ('error','reconnecting','crashed'):
            self.status.setText(message.get('message','Studio error'))
            if kind=='crashed':
                self.enabled.blockSignals(True);self.enabled.setChecked(False);self.enabled.blockSignals(False)
                for control in self.route_controls:control.setEnabled(True)

    def record_toggle(self, enabled):
        if not self.controller.ready.is_set():
            self.record.blockSignals(True);self.record.setChecked(False);self.record.blockSignals(False)
            self.status.setText('Start Studio and wait for audio devices before recording.');return
        path=Path(self.controller.folder.name)/('recording-'+uuid.uuid4().hex+'.wav')
        self.controller.send({'type':'record','enabled':enabled,'path':str(path)})

    def replay_recording(self):
        if self.recorded and self.recorded.exists() and self.controller.ready.is_set() and self.monitor_device.currentData():
            target=Path(self.controller.folder.name)/('replay-'+uuid.uuid4().hex+'.wav');shutil.copyfile(self.recorded,target)
            self.controller.send({'type':'replay','path':str(target)})
        else:self.status.setText('Start Studio with a separate monitor device to audition this recording.')

    def save_recording(self):
        if self.recorded and self.recorded.exists():
            path,_=QtWidgets.QFileDialog.getSaveFileName(self,'Save processed Studio recording','','WAV audio (*.wav)')
            if path:
                try:shutil.copyfile(self.recorded,path)
                except OSError:self.status.setText('Could not save the recording.')

    def select_preset(self, *args):
        if self.loading:return
        self.selected=self.preset.currentData() or 'b0'
        self.patch=deepcopy(next(p for key,_,p in self.items() if key==self.selected));self.load_controls();self.changed()

    def reset(self):self.select_preset()

    def favorite_changed(self, enabled):
        if self.loading:return
        favorites=set(self.store['favorites']);favorites.add(self.selected) if enabled else favorites.discard(self.selected)
        self.store['favorites']=sorted(favorites);self.rebuild_presets();self.save_timer.start()

    def save_as(self, name=None):
        if not isinstance(name,str):name,ok=QtWidgets.QInputDialog.getText(self,'Save Studio preset','Name:');name=name if ok else ''
        if not name.strip():return
        if len(self.store['presets'])>=128:self.status.setText('Use at most 128 custom presets.');return
        identifier='u'+uuid.uuid4().hex
        self.store['presets'][identifier]={'name':name.strip()[:80],'patch':validate_patch(self.patch)}
        self.selected=identifier;self.rebuild_presets();self.load_controls();self.persist();self.window._init_hotkeys()

    def duplicate(self):
        name=next(name for key,name,_ in self.items() if key==self.selected);self.save_as(name+' copy')

    def save_preset(self):
        if self.selected.startswith('b'):self.save_as();return
        self.store['presets'][self.selected]['patch']=validate_patch(self.patch);self.persist()

    def delete(self):
        if self.selected.startswith('b'):self.status.setText('Built-in presets cannot be deleted; duplicate one to edit your own copy.');return
        self.store['presets'].pop(self.selected,None);self.store['hotkeys'].pop(self.selected,None)
        self.store['favorites']=[key for key in self.store['favorites'] if key!=self.selected]
        self.selected='b0';self.rebuild_presets();self.select_preset();self.persist();self.window._init_hotkeys()

    def import_preset(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,'Import Studio preset','','Studio JSON (*.json)')
        if not path:return
        try:
            value=read_json(path)
            if value.get('version')!=1 or not isinstance(value.get('name'),str):raise ValueError('Unsupported Studio preset file.')
            patch=validate_patch(value['patch']);self.patch=patch;self.save_as(value['name'])
        except (OSError,ValueError,TypeError,KeyError) as error:self.status.setText('Import failed: '+str(error))

    def export_preset(self):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,'Export Studio preset','','Studio JSON (*.json)')
        if path:
            try:
                name=next(name for key,name,_ in self.items() if key==self.selected)
                atomic_json(path,{'version':1,'name':name,'patch':validate_patch(self.patch)})
            except (OSError,ValueError) as error:self.status.setText('Export failed: '+str(error))

    def configured_hotkeys(self):
        return [('studio_preset_'+key,self.store['hotkeys'].get(key,'')) for key,_,_ in self.items()]

    def assign_shortcut(self):
        from vrchat_speech_assistant.button_shortcuts import ButtonShortcutDialog
        ButtonShortcutDialog(self.window,'studio_preset_'+self.selected,'Studio preset').exec()

    def action(self, action):
        if action=='studio_monitor' and not self.monitor_device.currentData():
            self.status.setText('Choose a separate monitor device before enabling monitoring.');return
        controls={'studio_bypass':self.bypass,'studio_monitor':self.monitor,'studio_mute':self.mute,'studio_toggle':self.enabled}
        if action in controls:controls[action].toggle()
        elif action=='studio_panic':self.controller.send({'type':'panic'});self.set_ptt(False);self.status.setText('PANIC — all Studio output muted. Use Resume output to restore it.')
        elif action=='studio_ptt':self.set_ptt(True)
        elif action=='studio_ptt_release':self.set_ptt(False)
        elif action in ('studio_next','studio_previous'):
            count=self.preset.count()
            if count:self.preset.setCurrentIndex((self.preset.currentIndex()+(1 if action=='studio_next' else -1))%count)
        elif action.startswith('studio_preset_'):
            index=self.preset.findData(action[len('studio_preset_'):])
            if index>=0:self.preset.setCurrentIndex(index)

    def set_ptt(self, enabled):
        self.ptt_held=enabled;self.controller.send({'type':'ptt','pressed':enabled}) if self.controller.active else None

    def osc_effect(self, address, *values):
        try:
            if len(values)!=3:raise ValueError('Use effect, parameter, value.')
            name,key,value=values;patch=deepcopy(self.patch)
            if name not in PARAMETERS or key not in (*PARAMETERS[name],'enabled'):raise ValueError('Unknown effect parameter.')
            if key=='enabled':
                if value not in (0,1,False,True):raise ValueError('Enabled must be 0 or 1.')
                value=bool(value)
            patch['effects'][name][key]=value
            self.patch=validate_patch(patch);self.load_controls();self.changed()
        except (ValueError,TypeError):self.status.setText('Invalid Studio OSC effect command.')

    def osc_preset(self, address, *values):
        if len(values)!=1 or not isinstance(values[0],str):return
        candidates=[identifier for identifier,name,_ in self.items() if values[0] in (identifier,name)]
        if len(candidates)==1:self.preset.setCurrentIndex(self.preset.findData(candidates[0]))
        else:self.status.setText('Studio preset name is missing or ambiguous.')

    def eventFilter(self, obj, event):
        if self.ptt_held and event.type() in (QtCore.QEvent.KeyRelease,QtCore.QEvent.ApplicationDeactivate):self.set_ptt(False)
        return False

    def close_studio(self):
        self.apply_timer.stop();self.save_timer.stop();self.persist();self.controller.close()
        QtWidgets.QApplication.instance().removeEventFilter(self)
