from abc import ABCMeta, abstractmethod
import six

from lymph.core.services import Service


@six.add_metaclass(ABCMeta)
class BaseServiceRegistry(object):

    ServiceCls = Service

    def __init__(self):
        self.cache = {}

    def on_start(self):
        pass

    def on_stop(self, **kwargs):
        pass

    def get(self, service_name, **kwargs):
        try:
            service = self.cache[service_name]
        except KeyError:
            service = self.ServiceCls(self.container, name=service_name)
            self.lookup(service, **kwargs)
            self.cache[service_name] = service
        return service

    def install(self, container):
        self.container = container

    @abstractmethod
    def discover(self):
        raise NotImplementedError

    @abstractmethod
    def lookup(self, container, service, watch=False, timeout=1):
        raise NotImplementedError

    @abstractmethod
    def register(self, container, service_name):
        raise NotImplementedError

    @abstractmethod
    def unregister(self, container, service_name):
        raise NotImplementedError
