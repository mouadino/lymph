from __future__ import absolute_import

import contextlib

import newrelic.agent

from lymph.tracing.base import BaseTracer


class NewRelicTracer(BaseTracer):
    @contextlib.contextmanager
    def trace_context(self, **metadata):
        transaction = newrelic.agent.current_transaction()
        with newrelic.agent.FunctionTrace(transaction, **metadata):
            yield

    def record_event(self, name, value):
        newrelic.agent.record_custom_metric(name, value)
