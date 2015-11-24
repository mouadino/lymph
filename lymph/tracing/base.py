import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseTracer(object):

    @abc.abstractmethod
    def trace_context(self, **metadata):
        pass

    @abc.abstractmethod
    def record_event(self, name, value):
        pass
