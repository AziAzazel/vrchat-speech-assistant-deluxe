import threading
import pytest
from vrchat_speech_assistant.live_chatbox import LiveChatbox, split_pages, utf16_units, ChatboxOutputError
from vrchat_speech_assistant.output_control import output_scope, OutputCancelled


class Clock:
    value = 0
    def now(self):
        return self.value
    def wait(self, deadline):
        self.value = max(self.value, deadline)


@pytest.mark.parametrize('text', ['word '*150, '日本語'*160, '🤖'*200, 'x'*500,
                                 'first\nsecond '*60, '𝕏'*200])
def test_pages_preserve_all_content_and_respect_vrchat_utf16_limit(text):
    pages = split_pages(text)
    assert len(pages) > 1
    assert all(0 < utf16_units(page) <= 144 for page in pages)
    assert ''.join(''.join(pages).split()) == ''.join(text.split())


def test_first_page_is_immediate_and_next_pages_follow_audio_clock_without_skipping():
    clock, sent = Clock(), []
    display = LiveChatbox('hello '*100, sent.append, clock=lambda: clock.value, wait=clock.wait)
    display.start()
    assert sent == [display.pages[0]]
    display.progress(0, 30)
    assert len(sent) == 1
    clock.value = 10
    display.progress(10, 30)
    assert sent == display.pages[:2]
    clock.value = 30
    display.progress(30, 30)
    assert sent == display.pages[:3]  # Never jump over unseen text.
    display.finish(with_speech=True)
    assert sent == display.pages


def test_text_only_pages_have_reading_time_instead_of_replacing_each_other_immediately():
    clock, times = Clock(), []
    display = LiveChatbox('word '*100, lambda text: times.append(clock.value), clock=clock.now, wait=clock.wait)
    display.start()
    display.finish()
    assert len(times) == len(display.pages)
    assert all(b-a >= 2 for a, b in zip(times, times[1:]))


def test_stop_prevents_every_remaining_page():
    event, sent = threading.Event(), []
    display = LiveChatbox('word '*100, sent.append)
    with output_scope(event):
        display.start()
        event.set()
        with pytest.raises(OutputCancelled):
            display.finish()
    assert sent == [display.pages[0]]


def test_cancellation_inside_osc_send_is_not_relabelled_as_an_error():
    def cancelled(text):
        raise OutputCancelled()
    with pytest.raises(OutputCancelled):
        LiveChatbox('first', cancelled).start()
    def failed(text):
        raise OSError('private details')
    with pytest.raises(ChatboxOutputError) as error:
        LiveChatbox('first', failed).start()
    assert 'private' not in str(error.value)
