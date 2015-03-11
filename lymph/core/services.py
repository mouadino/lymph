import hashlib
import logging
import random

import gevent
import six

from lymph.utils import observables
from lymph.exceptions import ConnectionError


logger = logging.getLogger(__name__)

# Event types propagated by Service when instances change.
ADDED = 'ADDED'
REMOVED = 'REMOVED'
UPDATED = 'UPDATED'


class ServiceInstance(object):
    def __init__(self, container, endpoint=None, identity=None, **info):
        self.container = container
        self.identity = identity if identity else hashlib.md5(endpoint.encode('utf-8')).hexdigest()
        self.update(endpoint, **info)
        self.connection = None

    def update(self, endpoint, log_endpoint=None, name=None, fqdn=None):
        self.endpoint = endpoint
        self.log_endpoint = log_endpoint
        self.name = name
        self.fqdn = fqdn

    def connect(self):
        self.connection = self.container.connect(self.endpoint)
        return self.connection

    def disconnect(self):
        if self.connection:
            self.container.disconnect(self.endpoint)
            self.connection = None

    def is_alive(self):
        if self.connection is None:
            self.connect()
        return self.connection.is_alive()


class Service(observables.Observable):

    def __init__(self, container, name=None, instances=()):
        super(Service, self).__init__()
        self.container = container
        self.name = name
        self.instances = {i.endpoint: i for i in instances}

    def __iter__(self):
        return six.itervalues(self.instances)

    def __len__(self):
        return len(self.instances)

    def identities(self):
        return list(self.instances.keys())

    def connect(self, tries=3):
        for _ in range(tries):
            choices = [i for i in self if i.is_alive()]
            if choices:
                instance = random.choice(choices)
                return instance.connection
            gevent.sleep(0.1)
        logger.info("no live instance for %s", self.name)
        raise ConnectionError("Can't establish connection with '%s' (gave up after %d tries)" % (self.name, tries))

    def disconnect(self):
        for instance in self:
            instance.disconnect()

    def remove(self, identity):
        try:
            instance = self.instances.pop(identity)
        except KeyError:
            pass
        else:
            instance.disconnect()
            self.notify_observers(REMOVED, instance)

    def update(self, identity, **info):
        if identity in self.instances:
            self.instances[identity].update(**info)
            self.notify_observers(UPDATED, self.instances[identity])
        else:
            instance = self.instances[identity] = ServiceInstance(self.container, **info)
            self.notify_observers(ADDED, instance)
