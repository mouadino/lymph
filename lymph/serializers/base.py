import abc
import datetime
import decimal
import functools
import json
import msgpack
import six


@six.add_metaclass(abc.ABCMeta)
class ExtensionTypeSerializer(object):
    @abc.abstractmethod
    def serialize(self, obj):
        raise NotImplementedError

    @abc.abstractmethod
    def deserialize(self, obj):
        raise NotImplementedError


class DatetimeSerializer(ExtensionTypeSerializer):
    format = '%Y-%m-%dT%H:%M:%SZ'

    def serialize(self, obj):
        return obj.strftime(self.format)

    def deserialize(self, obj):
        return datetime.datetime.strptime(obj, self.format)


class DateSerializer(DatetimeSerializer):
    format = '%Y-%m-%d'

    def deserialize(self, obj):
        return super(DateSerializer, self).deserialize(obj).date()


class TimeSerializer(DatetimeSerializer):
    format = '%H:%M:%SZ'

    def deserialize(self, obj):
        return super(TimeSerializer, self).deserialize(obj).time()


class StrSerializer(ExtensionTypeSerializer):
    def __init__(self, factory):
        self.factory = factory

    def serialize(self, obj):
        return str(obj)

    def deserialize(self, obj):
        return self.factory(obj)


class SetSerializer(ExtensionTypeSerializer):
    def serialize(self, obj):
        return list(obj)

    def deserialize(self, obj):
        return set(obj)


_extension_type_serializers = {
    'datetime': DatetimeSerializer(),
    'date': DateSerializer(),
    'time': TimeSerializer(),
    'Decimal': StrSerializer(decimal.Decimal),
    'set': SetSerializer()
}


class BaseSerializer(object):
    __serializers = {}
    __priorities = {}

    def __init__(self, type, priority, dumps=None, loads=None, load=None, dump=None):
        self._dumps = dumps
        self._loads = loads
        self._load = load
        self._dump = dump
        self._type = type

        self.__serializers[type] = self
        if priority in self.__priorities.values():
            raise ValueError("Priority %s is already used" % priority)
        self.__priorities[type] = priority

    @classmethod
    def get_instance(cls, type):
        """Get serializer instance corresponding to the given ``type``.

        :param type: string representing serialization type e.g. json, msgpack ...
        :return: Instance that serialize messages into given type.
        :raises KeyError: If the serialization type is unknown.

        """
        return cls.__serializers[type]

    @classmethod
    def get_available_serializations(cls):
        """Get available serializations format sorted by priority."""
        return sorted(cls.__serializers, key=cls.__priorities.__getitem__)

    def dump_object(self, obj):
        obj_type = type(obj)
        serializer = _extension_type_serializers.get(obj_type.__name__)
        if serializer:
            obj = {
                '__type__': obj_type.__name__,
                '_': serializer.serialize(obj),
            }
        return obj

    def load_object(self, obj):
        obj_type = obj.get('__type__')
        if obj_type:
            serializer = _extension_type_serializers.get(obj_type)
            return serializer.deserialize(obj['_'])
        return obj

    def dumps(self, obj):
        return self._dumps(obj, default=self.dump_object)

    def loads(self, s):
        return self._loads(s, object_hook=self.load_object)

    def dump(self, obj, f):
        return self._dump(obj, f, default=self.dump_object)

    def load(self, f):
        return self._load(f, object_hook=self.load_object)

    def __str__(self):
        return 'Serializer: %s' % self._type

    __repr__ = __str__


msgpack_serializer = BaseSerializer(
    'msgpack',
    priority=10,
    dumps=functools.partial(msgpack.dumps, use_bin_type=True),
    loads=functools.partial(msgpack.loads, encoding='utf-8'),
    dump=functools.partial(msgpack.dump, use_bin_type=True),
    load=functools.partial(msgpack.load, encoding='utf-8'),
)

json_serializer = BaseSerializer(
    'json',
    priority=20,
    dumps=json.dumps,
    loads=json.loads,
    dump=json.dump,
    load=json.load)
