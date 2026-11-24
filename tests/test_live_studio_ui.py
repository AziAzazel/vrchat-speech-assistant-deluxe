"""Studio controls edit the validated patch, preserve presets and share shortcuts."""
from copy import deepcopy
import json
from unittest.mock import Mock
import pytest
from PySide6 import QtWidgets, QtCore
from vrchat_speech_assistant.live_settings import validate_patch


@pytest.fixture
def studio(gui,monkeypatch,tmp_path):
    app,main=gui
    from vrchat_speech_assistant import live_studio
    monkeypatch.setattr(live_studio,'DATA_DIR',tmp_path)
    monkeypatch.setattr(main.VRCSpeechAssistantWindow,'_init_translator',lambda self:None)
    monkeypatch.setattr(main.VRCSpeechAssistantWindow,'_check_selected_speech_provider',lambda self:None)
    window=main.VRCSpeechAssistantWindow()
    yield window.live_studio
    window.close();app.processEvents()


def test_builtin_selection_sliders_and_bypass_feed_the_worker_snapshot(studio,monkeypatch):
    studio.preset.setCurrentIndex(studio.preset.findData('b1')) # Vocaloid
    assert studio.patch['effects']['pitch']['semitones']==5
    assert studio.patch['effects']['tune']['strength']==100
    studio.effect_controls['pitch','semitones'].number.setValue(8)
    studio.effect_controls['pitch','formant'].slider.setValue(100)
    assert studio.patch['effects']['pitch']['semitones']==8
    assert studio.patch['effects']['pitch']['formant']==-2
    configured=Mock();monkeypatch.setattr(studio.controller,'configure',configured)
    studio.action('studio_bypass');studio.apply()
    snapshot=configured.call_args.args[0]
    assert snapshot['bypass'] and snapshot['patch']==validate_patch(studio.patch)
    studio.action('studio_ptt');assert studio.ptt_held
    studio.window.roleplay_action('studio_ptt_release');assert not studio.ptt_held


def test_custom_preset_crud_json_and_favorites(studio,tmp_path,monkeypatch):
    studio.preset.setCurrentIndex(studio.preset.findData('b2'))
    studio.save_as('My anime');identifier=studio.selected
    assert identifier.startswith('u') and studio.store['presets'][identifier]['name']=='My anime'
    studio.favorite.setChecked(True);assert identifier in studio.store['favorites']
    studio.effect_controls['pitch','semitones'].number.setValue(10);studio.save_preset()
    exported=tmp_path/'export.json'
    monkeypatch.setattr(QtWidgets.QFileDialog,'getSaveFileName',lambda *args,**kw:(str(exported),''))
    studio.export_preset();data=json.loads(exported.read_text())
    assert data['patch']['effects']['pitch']['semitones']==10
    monkeypatch.setattr(QtWidgets.QFileDialog,'getOpenFileName',lambda *args,**kw:(str(exported),''))
    studio.import_preset();assert studio.selected!=identifier
    assert studio.patch==validate_patch(data['patch'])
    studio.duplicate();assert len(studio.store['presets'])==3
    studio.delete();assert len(studio.store['presets'])==2 and studio.selected=='b0'
    studio.persist();stored=json.loads(studio.path.read_text())
    assert stored['version']==1 and 'patch' not in stored['route']


def test_osc_rejects_unsafe_values_and_controls_harmonizer(studio):
    before=deepcopy(studio.patch)
    studio.osc_effect('/studio/effect','delay','feedback',100)
    assert studio.patch==before
    studio.osc_effect('/studio/effect','pitch','enabled',1)
    studio.osc_effect('/studio/effect','pitch','semitones',7)
    assert studio.effect_enabled['pitch'].isChecked()
    assert studio.effect_controls['pitch','semitones'].number.value()==7
    studio.harmony.setCurrentText('Octave Down')
    assert studio.patch['voices'][0]['pitch']==-12 and not studio.patch['voices'][1]['enabled']
    studio.voices.cellWidget(0,4).setValue(-.5)
    assert studio.patch['voices'][0]['pan']==-.5 and studio.patch['harmony']=='Custom'
    studio.osc_preset('/studio/preset','Robot')
    assert studio.patch['effects']['vocoder']['mix']==100


def test_device_choices_are_explicit_and_invalid_routes_do_not_start(studio,monkeypatch):
    devices=[{'key':'api | Mic','name':'Mic','inputs':1,'outputs':0},
             {'key':'api | Cable','name':'CABLE Input','inputs':0,'outputs':2}]
    studio.on_devices(devices)
    started=Mock();monkeypatch.setattr(studio.controller,'start',started)
    studio.enabled.setChecked(True);assert not studio.enabled.isChecked();started.assert_not_called()
    studio.input.setCurrentIndex(studio.input.findData('api | Mic'))
    studio.output.setCurrentIndex(studio.output.findData('api | Cable'))
    studio.enabled.setChecked(True);started.assert_called_once()
    assert not studio.input.isEnabled() # format/device changes require explicit stop
    studio.enabled.setChecked(False);assert studio.input.isEnabled()


def test_presets_participate_in_existing_shortcut_conflict_registry(studio):
    studio.store['hotkeys']['b1']='Ctrl+Alt+1'
    assert ('studio_preset_b1','Ctrl+Alt+1') in studio.window.configured_hotkeys()
    with pytest.raises(ValueError):studio.window.validate_action_shortcut('studio_toggle','Ctrl+Alt+1')
    studio.window.save_action_shortcut('studio_preset_b1','Ctrl+Alt+2')
    assert studio.store['hotkeys']['b1']=='Ctrl+Alt+2'
    studio.window.roleplay_action('studio_preset_b1')
    assert studio.selected=='b1'
