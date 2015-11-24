from __future__ import absolute_import, unicode_literals

import functools

import gevent
import newrelic.agent
import newrelic.config
from newrelic.api.external_trace import ExternalTrace

from lymph.core import trace
from lymph.core.plugins import Plugin
from lymph.core import rpc
from lymph.core.interfaces import DeferredReply
from lymph.web.interfaces import WebServiceInterface


def with_trace_id(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        newrelic.agent.add_custom_parameter('trace_id', trace.get_id())
        return func(*args, **kwargs)
    return wrapped


def pre_request_send(msg, action=None):
    start_tracer(msg.subject, msg.headers)


def start_tracer(subject, headers):
    transaction = newrelic.agent.current_transaction()
    if not transaction:
        return
    trace_headers = ExternalTrace.generate_request_headers(transaction)
    headers.update(trace_headers)

    # Fake remote url to allow newrelic to extract tracing information, since
    # external tracing assume http as transport.
    url = 'lymph+rpc://{}/{}'.format(*subject.split('.'))
    tracer = ExternalTrace(transaction, library=transaction.settings.app_name, url=url)
    tracer.__enter__()

    greenlet = gevent.getcurrent()
    greenlet._newrelic_tracer = tracer


def on_reply_received(_, channel, action=None):
    channel.on_new_message(stop_tracer)


def stop_tracer(reply_msg):
    greenlet = gevent.getcurrent()
    tracer = getattr(greenlet, '_newrelic_tracer', None)
    if tracer:
        # Remote errors are tracked differently, we ignore them here.
        tracer.__exit__(None, None, None)
        if 'X-NewRelic-ID' in reply_msg.headers:
            tracer.process_response_headers(reply_msg.headers)


def pre_reply_send(req_msg, reply_msg, action=None):
    tracing_headers = {
        k: v
        for k, v in req_msg.headers.items()
        if k.startswith('X-NewRelic')
    }
    reply_msg.headers.update(tracing_headers)


def trace_rpc_method(method, get_subject):
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        transaction = newrelic.agent.current_transaction()
        with newrelic.agent.FunctionTrace(transaction, name=get_subject(self), group='Python/RPC'):
            return method(self, *args, **kwargs)

    return wrapped


class NewrelicPlugin(Plugin):
    def __init__(self, container, config_file=None, environment=None, app_name=None, **kwargs):
        super(NewrelicPlugin, self).__init__()
        self.container = container
        self.container.error_hook.install(self.on_error)
        self.container.http_request_hook.install(self.on_http_request)
        newrelic.agent.initialize(config_file, environment)
        settings = newrelic.agent.global_settings()
        if app_name:
            settings.app_name = app_name
            # `app_name` requires post-processing which is only triggered by
            # initialize(). We manually trigger it again with undocumented api.
            newrelic.config._process_app_name_setting()

        self._install_rpc_handlers()

    def _install_rpc_handlers(self):
        rpc_server = self.container.server

        rpc_server.observe(rpc.PRE_REQUEST_SEND, pre_request_send)
        rpc_server.observe(rpc.PRE_REPLY_SEND, pre_reply_send)
        rpc_server.observe(rpc.ON_REPLY_RECEIVED, on_reply_received)

        # Deferred calls are handled differently, since newrelic is limited to only
        # works inside one greenlet (transaction are not thread safe).
        DeferredReply.get = trace_rpc_method(DeferredReply.get, lambda deferred: deferred.subject)

    def on_interface_installation(self, interface):
        self._wrap_methods(interface.methods)
        self._wrap_methods(interface.event_handlers)
        if isinstance(interface, WebServiceInterface):
            interface.application = newrelic.agent.wsgi_application()(interface.application)

    def _wrap_methods(self, methods):
        for name, method in methods.items():
            method.decorate(with_trace_id)
            method.decorate(newrelic.agent.background_task())

    def on_error(self, exc_info, **kwargs):
        newrelic.agent.add_custom_parameter('trace_id', trace.get_id())
        newrelic.agent.record_exception(exc_info)

    def on_http_request(self, request, rule, kwargs):
        newrelic.agent.set_transaction_name("%s %s" % (request.method, rule))
        newrelic.agent.add_custom_parameter('trace_id', trace.get_id())
