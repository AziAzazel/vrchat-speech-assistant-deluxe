"""Subtitle timing, routing and cancellation without physical audio hardware."""
import threading
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from vrchat_speech_assistant import media_playback as media
from vrchat_speech_assistant.output_control import output_scope, OutputCancelled

SRT = '1\n00:00:00,000 --> 00:00:01,000\n<i>Zażółć</i> &amp; ポイ\n\n2\n00:00:02.000 --> 00:00:03.000\nSecond\nline\n'


def test_srt_unicode_timestamps_markup_overlap_and_limit(tmp_path):
    path = tmp_path/'subtitles.srt'
    for encoding in ('utf-8-sig', 'utf-16'):
        path.write_text(SRT, encoding=encoding)
        cues = media.load_srt(path)
        assert media.caption_at(cues, .5) == 'Zażółć & ポイ'
        assert media.caption_at(cues, 1.5) == ''
        assert media.caption_at(cues, 2.1) == 'Second line'
    path.write_text('1\n00:00:00,000 --> 00:00:01,000\nŻółć', encoding='cp1250')
    assert media.load_srt(path)[0].text == 'Żółć'
    assert media.caption_at([media.Cue(0, 3, 'a'), media.Cue(1, 2, 'b')], 1.5) == 'a b'
    assert len(media.caption_at([media.Cue(0, 3, 'x'*200)], 1)) == 144


@pytest.mark.parametrize('bad', ['', '1\nbad timestamp\nhello', '1\n00:00:02,000 --> 00:00:01,000\nhello'])
def test_invalid_srt_rejected(bad):
    with pytest.raises(ValueError):
        media.parse_srt(bad)


def test_fast_cues_coalesce_to_latest_instead_of_queueing():
    client = Mock()
    sender = media.CaptionSender(client)
    sender.update('first', 0)
    sender.update('obsolete', .5)
    sender.update('latest', 1.6)
    assert [call.args[1][0] for call in client.send_message.call_args_list] == ['first', 'latest']
    sender.clear()
    assert client.send_message.call_args.args[1][0] == ''


def fake_player(monkeypatch, positions):
    mixer = Mock()
    values = iter(positions)
    state = {'position': 0}
    def busy():
        try:
            state['position'] = next(values)
            return True
        except StopIteration:
            return False
    mixer.music.get_busy.side_effect = busy
    mixer.music.get_pos.side_effect = lambda: state['position']
    import pygame
    monkeypatch.setattr(pygame, 'mixer', mixer)
    monkeypatch.setattr(media.time, 'sleep', lambda _: None)
    return mixer


def test_audio_clock_and_positive_offset(monkeypatch, tmp_path):
    captions = tmp_path/'timed.srt'
    captions.write_text('1\n00:00:01,000 --> 00:00:02,000\nAligned', encoding='utf-8')
    mixer = fake_player(monkeypatch, [1000, 1500, 1600])
    client = Mock()
    media.MediaSpeech('track.mp3', str(captions), 500, client=client).speech('', '', 'Cable')
    assert client.send_message.call_args_list[0].args[1][0] == 'Aligned'
    mixer.pre_init.assert_called_once_with(devicename='Cable')
    mixer.music.load.assert_called_once_with('track.mp3')
    mixer.quit.assert_called_once()


def test_stop_cancels_audio_and_all_future_subtitles(monkeypatch, tmp_path):
    captions = tmp_path/'timed.srt'
    captions.write_text(SRT, encoding='utf-8')
    mixer = fake_player(monkeypatch, [0, 2500])
    client, event = Mock(), threading.Event()
    monkeypatch.setattr(media.time, 'sleep', lambda _: event.set())
    with output_scope(event), pytest.raises(OutputCancelled):
        media.MediaSpeech('track.wav', str(captions), client=client).speech('', '', 'Cable')
    assert [call.args[1][0] for call in client.send_message.call_args_list] == ['Zażółć & ポイ', '']
    mixer.quit.assert_called_once()


def test_audio_only_ignores_subtitles_and_never_contacts_osc(monkeypatch):
    mixer = fake_player(monkeypatch, [0])
    client = Mock()
    media.MediaSpeech('track.wav', 'unused.srt', output='Voice only', client=client).speech('', '', 'Cable')
    client.send_message.assert_not_called()
    mixer.music.play.assert_called_once()


def test_subtitles_only_use_clock_without_initializing_audio(monkeypatch, tmp_path):
    import pygame
    mixer, client = Mock(), Mock()
    monkeypatch.setattr(pygame, 'mixer', mixer)
    ticks = iter([0, 0, .5, 2])
    monkeypatch.setattr(media.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(media.time, 'sleep', lambda _: None)
    path = tmp_path/'captions.srt'
    path.write_text('1\n00:00:00,000 --> 00:00:01,000\nText', encoding='utf-8')
    media.MediaSpeech('not-needed.wav', str(path), output='Chatbox only', client=client).speech('', '', None)
    mixer.init.assert_not_called()
    assert [call.args[1][0] for call in client.send_message.call_args_list] == ['Text', '']


def test_indexed_timeline_matches_reference_across_overlap_gaps_and_rewind():
    cues = [media.Cue(0, 2, 'first'), media.Cue(1, 3, 'second'), media.Cue(3, 4, 'third'),
            media.Cue(1, 1.5, 'x'*180)]
    timeline = media.CaptionTimeline(cues)
    for position in (-1, 0, .5, 1, 1.49, 1.5, 2, 3, 4, 5, 1, 0, 3.5):
        assert timeline.at(position) == media.caption_at(cues, position)


def test_large_srt_timeline_caches_text_between_boundaries():
    cues = [media.Cue(index*2, index*2+1, str(index)) for index in range(10000)]
    timeline = media.CaptionTimeline(cues)
    assert timeline.at(.2) == '0'
    cursor = timeline._cursor
    assert timeline.at(.8) == '0' and timeline._cursor == cursor
    assert timeline.at(19998.5) == '9999'
    assert timeline.at(19999.1) == ''
