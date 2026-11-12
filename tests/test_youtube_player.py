from types import SimpleNamespace
from unittest.mock import Mock
import sys
import pytest
from vrchat_speech_assistant import youtube_player as youtube

VIDEO = 'abcdefghijk'


@pytest.mark.parametrize('link', [f'https://www.youtube.com/watch?v={VIDEO}&si=share',
                                 f'https://youtu.be/{VIDEO}', f'youtube.com/shorts/{VIDEO}',
                                 f'https://m.youtube.com/live/{VIDEO}', f'https://music.youtube.com/watch?v={VIDEO}'])
def test_only_canonical_youtube_video_url_is_opened(link):
    assert youtube.youtube_url(link) == f'https://www.youtube.com/watch?v={VIDEO}'


@pytest.mark.parametrize('link', ['file:///C:/secret', 'https://youtube.com.evil/watch?v=abcdefghijk',
                                 'https://youtube.com@evil.example/watch?v=abcdefghijk',
                                 'http://youtube.com/watch?v=abcdefghijk', 'https://youtube.com/playlist?list=x',
                                 'https://youtube.com/watch?v=bad', 'https://youtube.com:8080/watch?v=abcdefghijk',
                                 'javascript:alert(1)', '--some-argument'])
def test_non_video_links_cannot_launch_other_targets(link):
    with pytest.raises(ValueError):
        youtube.youtube_url(link)


def test_video_timestamp_is_preserved_without_extra_query_parameters():
    assert youtube.youtube_url(f'https://youtu.be/{VIDEO}?t=1m20s&autoplay=1') == f'https://www.youtube.com/watch?v={VIDEO}&t=1m20s'


@pytest.fixture
def native(monkeypatch, tmp_path):
    edge = tmp_path/'msedge.exe'
    edge.touch()
    monkeypatch.setattr(youtube, 'find_edge', lambda: edge)
    monkeypatch.setattr(youtube.sys, 'platform', 'win32')
    job, process, thread = Mock(), Mock(), Mock()
    jobs = Mock(JobObjectExtendedLimitInformation=9, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE=0x2000)
    jobs.CreateJobObject.return_value = job
    jobs.QueryInformationJobObject.return_value = {'BasicLimitInformation': {'LimitFlags': 0}}
    processes, events, api = Mock(), Mock(), Mock()
    processes.CreateProcess.return_value = process, thread, 123, 456
    events.WAIT_TIMEOUT = 258
    events.WaitForSingleObject.return_value = 258
    for name, module in [('win32job', jobs), ('win32process', processes), ('win32event', events), ('win32api', api)]:
        monkeypatch.setitem(sys.modules, name, module)
    return SimpleNamespace(jobs=jobs, processes=processes, events=events, api=api,
                           job=job, process=process, thread=thread)


def test_owned_browser_starts_suspended_and_stop_closes_only_its_job(native, tmp_path):
    player = youtube.EdgePlayer(tmp_path/'own profile')
    player.start(f'https://youtu.be/{VIDEO}')
    assert native.processes.CreateProcess.call_args.args[5] == 4
    arguments = native.processes.CreateProcess.call_args.args[1]
    assert '--user-data-dir=' in arguments and '--app=https://www.youtube.com/watch?' in arguments
    native.jobs.AssignProcessToJobObject.assert_called_once_with(native.job, native.process)
    native.processes.ResumeThread.assert_called_once_with(native.thread)
    native.thread.Close.assert_called_once()
    assert player.is_running
    player.stop()
    native.job.Close.assert_called_once()
    native.process.Close.assert_called_once()
    assert not player.is_running
    native.api.TerminateProcess.assert_not_called()
    player.stop()  # Repeated Stop is harmless.
    assert native.job.Close.call_count == 1


def test_failed_job_assignment_never_leaves_an_unowned_suspended_browser(native, tmp_path):
    native.jobs.AssignProcessToJobObject.side_effect = RuntimeError('assignment failed')
    player = youtube.EdgePlayer(tmp_path/'profile')
    with pytest.raises(RuntimeError):
        player.start(f'https://youtu.be/{VIDEO}')
    native.processes.ResumeThread.assert_not_called()
    native.api.TerminateProcess.assert_called_once_with(native.process, 1)
    native.job.Close.assert_called_once()
    native.process.Close.assert_called_once()
    native.thread.Close.assert_called_once()
    assert not player.is_running
