import hashlib
import logging
import random

import six

from lymph.utils import observables
from lymph.exceptions import NotConnected, UnsupportedSerialization
from lymph.serializers.base import BaseSerializer


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

    def update(self, endpoint, log_endpoint=None, name=None, supported_serializations=None):
        self.endpoint = endpoint
        self.log_endpoint = log_endpoint
        self.name = name
        self.supported_serializations = supported_serializations

    def get_best_serialization_type(self):
        """Get best serialization that both client and instance support.

        Find the first match from instance's ``supported_serialization`` that is
        also supported by the current client, since client and service may be using
        different lymph versions with different serializations type available.

        :return: Serialization type as string or :global:``DEFAULT_CONTENT_TYPE``
                 if instance doesn't have any preference.
        :raises: UnsupportedSerialization in case not match was found.
        """
        client_serializations = BaseSerializer.get_available_serializations()
        if self.supported_serializations is None:
            return client_serializations[0]
        for res in self.supported_serializations:
            if res in client_serializations:
                return res
        raise UnsupportedSerialization(
            'No serialization found'
        )

    def connect(self):
        self.connection = self.container.connect(self.endpoint)
        return self.connection

    def disconnect(self):
        if self.connection:
            self.container.disconnect(self.endpoint)
            self.connection = None

    def is_alive(self):
        return self.connection is None or self.connection.is_alive()


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

    def connect(self):
        choices = [i for i in self if i.is_alive()]
        if not choices:
            logger.info("no live instance for %s", self.name)
            choices = list(self.instances.values())
        if not choices:
            raise NotConnected()
        instance = random.choice(choices)
        return instance, instance.connect()

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
