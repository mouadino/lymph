import time
import random

import gevent

from lymph.exceptions import RetryableError, Timeout


class Retry(object):
    retry_error = RetryableError
    failure_error = Timeout

    def __init__(self, timeout, delay=.1, backoff=2, max_jitter=.8, max_delay=None):
        self._timeout = timeout
        self._delay = delay
        self._backoff = backoff
        self._max_jitter = max_jitter
        self._max_delay = max_delay

    def execute(self, func, *args, **kwargs):
        delay = self._delay
        with gevent.Timeout(self._timeout, self.failure_error):
            while 1:
                try:
                    return func(*args, **kwargs)
                except self.retry_error:
                    delay *= self._backoff
                    delay += random.random() * self._max_jitter
                    if self._max_delay is not None:
                        delay = min(delay, self._max_delay)
                    gevent.sleep(delay)
