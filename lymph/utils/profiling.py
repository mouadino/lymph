import cProfile
import functools


def profile(sortby='cumulative'):
    def _profile(func):
        @functools.wraps(func)
        def _inner(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()
            try:
                return func(*args, **kwargs)
            finally:
                profiler.disable()
                profiler.print_stats(sortby)
        return _inner
    return _profile
