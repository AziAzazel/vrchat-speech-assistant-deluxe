"""Bounded diagnostic logs without transcripts or exception messages."""
import faulthandler
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os
import sys
import threading
import traceback

DATA_DIR = Path(os.getenv("APPDATA") or os.getenv('XDG_CONFIG_HOME') or Path.home() / ".config") / "VRChat Speech Assistant"
_fatal_file = None


def record_failure(stage, exc_type, tb):
    # Exception messages from remote providers can include submitted text/keys.
    frames = "".join(traceback.format_list([
        (frame.filename, frame.lineno, frame.name, None)
        for frame in traceback.extract_tb(tb)
    ]))
    logging.getLogger("deluxe").error("%s failed (%s)\n%s", stage, exc_type.__name__, frames)


def setup_logging():
    global _fatal_file
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("deluxe")
    if logger.handlers:
        return
    handler = RotatingFileHandler(log_dir / "application.log", maxBytes=1_000_000,
                                  backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(threadName)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    sys.excepthook = lambda kind, value, tb: record_failure("Uncaught exception", kind, tb)
    threading.excepthook = lambda args: record_failure("Worker", args.exc_type, args.exc_traceback)
    fatal = log_dir / "native-crash.log"
    if fatal.exists() and fatal.stat().st_size > 1_000_000:
        fatal.replace(log_dir / "native-crash.previous.log")
    _fatal_file = fatal.open("a", encoding="utf-8")
    faulthandler.enable(file=_fatal_file, all_threads=True)
    logger.info("Starting deluxe; Python %s; platform %s", sys.version.split()[0], sys.platform)
