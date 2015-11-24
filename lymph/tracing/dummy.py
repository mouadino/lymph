import contextlib

from lymph.tracing.base import BaseTracer


class DummyTracer(BaseTracer):
    @contextlib.contextmanager
    def trace_context(self, **_):
        yield

    def record_event(self, name, value):
        pass
