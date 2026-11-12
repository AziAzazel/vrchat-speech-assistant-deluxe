import configparser
from unittest.mock import Mock
import pytest
from vrchat_speech_assistant.settings_store import SettingsStore


def config(value='first'):
    parser = configparser.ConfigParser(interpolation=None)
    parser['SPEECH'] = {'voice': value, 'pitch': '-15'}
    return parser


def test_unchanged_saves_do_not_rewrite_and_deleted_file_is_restored(tmp_path):
    path = tmp_path/'config.ini'
    store, parser = SettingsStore(path), config()
    assert store.save(parser)
    before = path.stat().st_mtime_ns
    assert not store.save(parser)
    assert not SettingsStore(path).save(parser)
    assert path.stat().st_mtime_ns == before
    path.unlink()
    assert store.save(parser)
    assert 'first' in path.read_text()


def test_nested_batch_writes_final_state_once_and_rollback_does_not_flush(tmp_path, monkeypatch):
    store, parser = SettingsStore(tmp_path/'config.ini'), config()
    commit = Mock(wraps=store._commit)
    monkeypatch.setattr(store, '_commit', commit)
    with store.batch():
        store.save(parser)
        with store.batch():
            parser['SPEECH']['voice'] = 'Japanese'
            store.save(parser)
        assert not store.path.exists()
    assert commit.call_count == 1 and 'Japanese' in store.path.read_text()
    before = store.path.read_bytes()
    with pytest.raises(ValueError), store.batch():
        parser['SPEECH']['voice'] = 'not committed'
        store.save(parser)
        raise ValueError()
    assert store.path.read_bytes() == before


def test_failed_atomic_replace_preserves_previous_file_and_cleans_temporary(tmp_path, monkeypatch):
    from vrchat_speech_assistant import settings_store
    path = tmp_path/'config.ini'
    store, parser = SettingsStore(path), config()
    store.save(parser)
    before = path.read_bytes()
    parser['SPEECH']['voice'] = 'new'
    monkeypatch.setattr(settings_store.os, 'replace', Mock(side_effect=OSError('disk failure')))
    with pytest.raises(OSError):
        store.save(parser)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_save_error_callback_is_used_without_exposing_setting_values(tmp_path, monkeypatch):
    from vrchat_speech_assistant import settings_store
    errors = []
    store = SettingsStore(tmp_path/'config.ini', errors.append)
    monkeypatch.setattr(settings_store.os, 'replace', Mock(side_effect=OSError('disk failure')))
    assert not store.save(config())
    assert len(errors) == 1
