"""Open normal YouTube playback in an owned Microsoft Edge app window.

No media extraction, download API, browser automation or caption scraping.
A Windows job owns this dedicated profile's processes, never ordinary Edge tabs.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, urlencode, urlsplit


def youtube_url(value):
    value = value.strip()
    if len(value) > 2048:
        raise ValueError('Paste a YouTube video link.')
    if '://' not in value:
        value = 'https://' + value
    try:
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError()
        host = parsed.hostname or ''
        query = parse_qs(parsed.query)
        path = parsed.path.strip('/').split('/')
        if host in ('youtu.be', 'www.youtu.be') and len(path) == 1:
            video = path[0]
        elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
            if path == ['watch']:
                video = query.get('v', [''])[0]
            elif len(path) == 2 and path[0] in ('shorts', 'live', 'embed'):
                video = path[1]
            else:
                raise ValueError()
        else:
            raise ValueError()
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
            raise ValueError()
        parameters = {'v': video}
        timestamp = query.get('t', query.get('start', ['']))[0]
        if timestamp and re.fullmatch(r'(?:\d+h)?(?:\d+m)?(?:\d+s?)?', timestamp):
            parameters['t'] = timestamp
        return 'https://www.youtube.com/watch?' + urlencode(parameters)
    except (ValueError, IndexError):
        raise ValueError('Use an HTTPS YouTube video link (watch, youtu.be, Shorts or live).') from None


def find_edge():
    candidates = [Path(os.environ[name]) / 'Microsoft/Edge/Application/msedge.exe'
                  for name in ('PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA') if os.environ.get(name)]
    found = shutil.which('msedge.exe')
    if found:
        candidates.insert(0, Path(found))
    return next((path for path in candidates if path.is_file()), None)


class EdgePlayer:
    def __init__(self, profile):
        self.profile = Path(profile)
        self._job = None
        self._process = None

    @property
    def is_running(self):
        if self._process is None:
            return False
        import win32event
        return win32event.WaitForSingleObject(self._process, 0) == win32event.WAIT_TIMEOUT

    def start(self, url):
        target = youtube_url(url)
        self._launch(target)
        return target

    def _launch(self, target):
        if sys.platform != 'win32':
            raise ValueError('YouTube playback requires Windows and Microsoft Edge.')
        executable = find_edge()
        if executable is None:
            raise ValueError('Microsoft Edge was not found. Install Edge to use YouTube playback.')
        import win32api
        import win32job
        import win32process
        self.stop()
        self.profile.mkdir(parents=True, exist_ok=True)
        argv = [str(executable), '--app=' + target, '--user-data-dir=' + str(self.profile.resolve()),
                '--no-first-run', '--no-default-browser-check', '--disable-background-mode']
        job, process, thread = None, None, None
        try:
            job = win32job.CreateJobObject(None, None)
            information = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
            information['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, information)
            # Assign ownership before Edge can spawn renderer/audio processes.
            process, thread, _, _ = win32process.CreateProcess(
                str(executable), subprocess.list2cmdline(argv), None, None, False,
                0x00000004, None, None, win32process.STARTUPINFO())  # CREATE_SUSPENDED
            win32job.AssignProcessToJobObject(job, process)
            win32process.ResumeThread(thread)
            self._job, self._process = job, process
        except Exception:
            try:
                if job is not None:
                    job.Close()
            finally:
                if process is not None:
                    try:
                        win32api.TerminateProcess(process, 1)
                    except Exception:
                        pass  # The owned job may already have terminated Edge.
                    finally:
                        process.Close()
            raise
        finally:
            if thread is not None:
                thread.Close()

    def stop(self):
        job, process = self._job, self._process
        self._job = self._process = None
        if job is not None:
            job.Close()  # Kills only this job, including Edge audio/renderer children.
        if process is not None:
            import win32event
            win32event.WaitForSingleObject(process, 3000)
            process.Close()
