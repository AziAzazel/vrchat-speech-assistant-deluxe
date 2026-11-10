"""Stage durations only: never log content, credentials or provider messages."""
from contextlib import contextmanager
import logging
from time import perf_counter


@contextmanager
def stage_timer(stage):
    started = perf_counter()
    try:
        yield
    finally:
        logging.getLogger('deluxe.timings').info('Stage %s duration_seconds=%.3f', stage, perf_counter()-started)
