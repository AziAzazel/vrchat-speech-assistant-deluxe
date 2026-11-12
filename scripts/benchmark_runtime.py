"""Synthetic, reproducible component measurements; not a whole-app FPS test.

Run with PYTHONPATH=src python scripts/benchmark_runtime.py.
Optionally use --baseline-ref v1.21.0rc4 to compare provider module imports.
No cloud calls, private config or physical audio devices are used.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time


def main():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument('--baseline-ref')
    options = arguments.parse_args()
    with tempfile.TemporaryDirectory(prefix='deluxe-benchmark-') as directory:
        root = Path(directory)
        os.environ.update(APPDATA=directory, PYGAME_HIDE_SUPPORT_PROMPT='1')
        try:
            results = measure(root, options.baseline_ref)
            print(json.dumps(results, indent=2))
        finally:
            import faulthandler
            import logging
            from vrchat_speech_assistant import diagnostics
            faulthandler.disable()
            if diagnostics._fatal_file:
                diagnostics._fatal_file.close()
            for handler in list(logging.getLogger('deluxe').handlers):
                handler.close()
                logging.getLogger('deluxe').removeHandler(handler)


def measure(root, baseline_ref):
    from vrchat_speech_assistant.media_playback import Cue, caption_at, CaptionTimeline
    from vrchat_speech_assistant.settings_store import SettingsStore
    import configparser
    cues = [Cue(index*2, index*2+1.8, f'Line {index}') for index in range(4000)]
    positions = [index*.04 for index in range(3000)]
    reference_times, indexed_times = [], []
    for _ in range(3):
        started = time.perf_counter()
        expected = [caption_at(cues, position) for position in positions]
        reference_times.append(time.perf_counter()-started)
        started = time.perf_counter()
        timeline = CaptionTimeline(cues)
        actual = [timeline.at(position) for position in positions]
        indexed_times.append(time.perf_counter()-started)
        assert actual == expected
    class CountedStore(SettingsStore):
        writes = 0
        def _commit(self, content):
            changed = super()._commit(content)
            self.writes += int(changed)
            return changed
    parser = configparser.ConfigParser()
    parser['SPEECH'] = {'voice': 'example'}
    repeated = CountedStore(root/'repeated.ini')
    for _ in range(200):
        repeated.save(parser)
    batched = CountedStore(root/'batched.ini')
    with batched.batch():
        for index in range(100):
            parser['SPEECH']['voice'] = str(index)
            batched.save(parser)
    baseline = ''
    if baseline_ref:
        source = subprocess.check_output(['git', 'show', f'{baseline_ref}:src/vrchat_speech_assistant/providers.py'], text=True)
        path = root/'baseline_providers.py'
        path.write_text(source, encoding='utf-8')
        baseline = str(path)
    command = '''import importlib.util,json,sys,time
started=time.perf_counter()
if sys.argv[1]:
 spec=importlib.util.spec_from_file_location('baseline_providers',sys.argv[1])
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
else:
 import vrchat_speech_assistant.providers
print(json.dumps({'seconds':time.perf_counter()-started,'boto3_loaded':'boto3' in sys.modules}))'''
    imports = {'current': []}
    if baseline:
        imports['baseline'] = []
    for index in range(3):
        for label, path in ([('baseline', baseline)] if baseline else []) + [('current', '')]:
            environment = dict(os.environ, APPDATA=str(root/f'import-{label}-{index}'))
            result = subprocess.run([sys.executable, '-c', command, path], env=environment,
                                    capture_output=True, text=True, check=True)
            imports[label].append(json.loads(result.stdout))
    return {'srt_cues': len(cues), 'srt_positions': len(positions),
            'srt_reference_seconds_median': statistics.median(reference_times),
            'srt_indexed_seconds_median_including_index_build': statistics.median(indexed_times),
            'repeated_save_requests': 200, 'repeated_save_disk_writes': repeated.writes,
            'batched_update_requests': 100, 'batched_disk_writes': batched.writes,
            'provider_imports': imports}


if __name__ == '__main__':
    main()
