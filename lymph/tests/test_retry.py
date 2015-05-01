import unittest

import gevent

from lymph.exceptions import RetryableError, Timeout
from lymph.core.retry import Retry


class SomeRetryableError(RetryableError):
    pass


class RetryTest(unittest.TestCase):
    def test_always_failing_func_with_retryable_error(self):
        def func():
            raise SomeRetryableError()
        retry = Retry(1)
        with self.assertRaises(Timeout):
            retry.execute(func)

    def test_failing_func_with_no_retryable_error(self):
        def func():
            raise ValueError()
        retry = Retry(1)
        with self.assertRaises(ValueError):
            retry.execute(func)

    def test_successful_func(self):
        def func(ret):
            gevent.sleep(1)
            return ret
        retry = Retry(2)
        result = retry.execute(func, 'ok')
        self.assertEqual(result, 'ok')

    def test_timeouted_func(self):
        def func():
            gevent.sleep(2)
        retry = Retry(1)
        with self.assertRaises(Timeout):
            retry.execute(func)
