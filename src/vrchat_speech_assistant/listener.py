"""Owned capture thread with bounded listening and recoverable device failures."""
import threading
import speech_recognition


class BackgroundListener:
    def __init__(self, recognizer, microphone, callback, failure, generation=None):
        self.recognizer, self.microphone = recognizer, microphone
        self.callback, self.failure = callback, failure
        self.generation = generation
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run, name="microphone", daemon=True)

    def start(self):
        self.thread.start()

    def stop(self, wait_for_stop=False):
        self.stopped.set()
        if wait_for_stop:
            self.thread.join(timeout=2)

    def run(self):
        try:
            with self.microphone as source:
                while not self.stopped.is_set():
                    epoch = self.generation() if self.generation else None
                    try:
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=15)
                    except speech_recognition.WaitTimeoutError:
                        continue
                    if not self.stopped.is_set():
                        if self.generation:
                            self.callback(self.recognizer, audio, epoch)
                        else:
                            self.callback(self.recognizer, audio)
        except Exception as error:
            if not self.stopped.is_set():
                self.failure(error)
