from abc import ABCMeta, abstractmethod
import logging
import sys

import six


logger = logging.getLogger(__name__)


@six.add_metaclass(ABCMeta)
class BaseEventSystem(object):

    def __init__(self, container):
        self.container = container

    @classmethod
    def from_config(cls, config, **kwargs):
        return cls(**kwargs)

    def install(self, container):
        pass

    def on_start(self):
        pass

    def on_stop(self):
        pass

    def subscribe(self, container, handler):
        raise NotImplementedError

    def unsubscribe(self, container, handler):
        raise NotImplementedError

    @abstractmethod
    def emit(self, container, event):
        raise NotImplementedError


class MessageHandler(object):

    def __init__(self, event_system):
        self.event_system = event_system

    def on_message(self, body, message):
        try:
            self.handle_message(body, message)
        except:
            self.on_error(sys.exc_info())

    def on_error(self, exc_info):
        self.event_system.container.error_hook(exc_info)

    def handle_message(self, body, message):
        pass
