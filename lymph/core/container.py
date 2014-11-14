import json
import gc
import gevent
import gevent.queue
import gevent.pool
import logging
import os
import six

from lymph.core.events import Event
from lymph.core.rpc import ZeroRPCServer
from lymph.exceptions import RegistrationFailure, SocketNotCreated
from lymph.core.monitoring import Monitor
from lymph.core.services import ServiceInstance
from lymph.core.interfaces import DefaultInterface
from lymph.core import trace


logger = logging.getLogger(__name__)


def create_container(config):
    registry = config.create_instance('registry')
    event_system = config.create_instance('event_system')
    container = config.create_instance(
        'container',
        default_class='lymph.core.container:ServiceContainer',
        registry=registry,
        events=event_system,
    )
    return container


class ServiceContainer(object):

    rpc_server_cls = ZeroRPCServer

    def __init__(self, ip='127.0.0.1', port=None, registry=None, logger=None, events=None, node_endpoint=None, log_endpoint=None, service_name=None):
        self.rpc_server = self.rpc_server_cls(self, ip, port=port)
        self.node_endpoint = node_endpoint
        self.log_endpoint = log_endpoint
        self.service_name = service_name

        self.service_registry = registry
        self.event_system = events

        self.installed_interfaces = {}
        self.installed_plugins = []

        self.monitor = Monitor(self)

        self.install(DefaultInterface)
        registry.install(self)
        if events:
            events.install(self)

    @property
    def endpoint(self):
        return self.rpc_server.endpoint

    @property
    def identity(self):
        return self.rpc_server.identity

    @classmethod
    def from_config(cls, config, **explicit_kwargs):
        kwargs = dict(config)
        kwargs.pop('class', None)
        kwargs.setdefault('node_endpoint', os.environ.get('LYMPH_NODE'))
        for key, value in six.iteritems(explicit_kwargs):
            if value is not None:
                kwargs[key] = value
        return cls(**kwargs)

    def install(self, cls, **kwargs):
        obj = cls(self, **kwargs)
        self.installed_interfaces[obj.service_type] = obj
        return obj

    def install_plugin(self, cls, **kwargs):
        plugin = cls(self, **kwargs)
        self.installed_plugins.append(plugin)

    def stats(self):
        hub = gevent.get_hub()
        threadpool, loop = hub.threadpool, hub.loop
        s = {
            'endpoint': self.endpoint,
            'identity': self.identity,
            'service': self.service_name,
            'gevent': {
                'threadpool': {
                    'size': threadpool.size,
                    'maxsize': threadpool.maxsize,
                },
                'active': loop.activecnt,
                'pending': loop.pendingcnt,
                'iteration': loop.iteration,
                'depth': loop.depth,
            },
            'gc': {
                'garbage': len(gc.garbage),
                'collections': gc.get_count(),
            },
            'rpc': self.rpc_server.stats,
        }
        for name, interface in six.iteritems(self.installed_interfaces):
            s[name] = interface.stats()
        return s

    def get_shared_socket_fd(self, port):
        fds = json.loads(os.environ.get('LYMPH_SHARED_SOCKET_FDS', '{}'))
        try:
            return fds[str(port)]
        except KeyError:
            raise SocketNotCreated

    @property
    def service_types(self):
        return self.installed_interfaces.keys()

    def subscribe(self, handler, **kwargs):
        return self.event_system.subscribe(handler, **kwargs)

    def unsubscribe(self, handler):
        self.event_system.unsubscribe(self, handler)

    def get_instance_description(self, service_type=None):
        return {
            'endpoint': self.endpoint,
            'identity': self.identity,
            'log_endpoint': self.log_endpoint,
        }

    def start(self, register=True):
        self.running = True
        logger.info('starting %s at %s (pid=%s)', ', '.join(self.service_types), self.endpoint, os.getpid())
        self.monitor.start()
        self.service_registry.on_start()
        self.event_system.on_start()
        self.rpc_server.start()

        for service in six.itervalues(self.installed_interfaces):
            service.on_start()
            service.configure({})

        if register:
            for service_type, service in six.iteritems(self.installed_interfaces):
                if not service.register_with_coordinator:
                    continue
                try:
                    self.service_registry.register(service_type)
                except RegistrationFailure:
                    logger.error("registration failed %s, %s", service_type, service)
                    self.stop()

    def stop(self):
        self.running = False
        for service in six.itervalues(self.installed_interfaces):
            service.on_stop()
        self.event_system.on_stop()
        self.service_registry.on_stop()
        self.monitor.stop()
        self.rpc_server.stop()

    def join(self):
        self.rpc_server.join()

    def connect(self, endpoint):
        for service in six.itervalues(self.installed_interfaces):
            service.on_connect(endpoint)
        return self.rpc_server.connect(endpoint)

    def disconnect(self, endpoint, socket=False):
        self.rpc_server.disconnect()
        for service in six.itervalues(self.installed_interfaces):
            service.on_disconnect(endpoint)

    def lookup(self, address):
        if '://' not in address:
            return self.service_registry.get(address)
        return ServiceInstance(self, address)

    def discover(self):
        return self.service_registry.discover()

    # FIXME (Mouad): Now there is 2 prepare_headers() method, one
    # in core/container.py another in core/rpc.py
    def prepare_headers(self, headers):
        headers = headers or {}
        headers.setdefault('trace_id', trace.get_id())
        return headers

    def send_request(self, address, subject, body, headers=None):
        return self.rpc_server.send_request(address, subject, body, headers=None)

    def emit_event(self, event_type, payload, headers=None):
        headers = self.prepare_headers(headers)
        event = Event(event_type, payload, source=self.identity, headers=headers)
        self.event_system.emit(event)
