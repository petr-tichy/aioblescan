from collections import UserDict
from decimal import Decimal
from time import monotonic


class BaseDescriptor:
    def __init__(self, name, ttl=60):
        self.name = name
        self.ttl = float(ttl)

    def __set__(self, instance, data):
        data = self.convert(data)
        cache = instance.cache.get(self.name)
        timestamp = instance.timestamp.get(self.name, -self.ttl)
        now = monotonic()
        if cache is None or not self.equals(data, cache) or (now - timestamp) > self.ttl:
            instance.cache[self.name] = data
            instance.timestamp[self.name] = now
            instance.data[self.name] = str(data)
            instance.data['changed'] = True

    def __delete__(self, instance):
        del instance.data[self.name]

    def convert(self, data):
        return str(data)

    def equals(self, new, old):
        return new == old


class AttributeDescriptor(BaseDescriptor):
    def __init__(self, name):
        super().__init__(name)

    def __set__(self, instance, value):
        if instance.data.get(self.name) is not None:
            raise AttributeError
        instance.data[self.name] = value

    def __delete__(self, instance):
        pass


class ReadingDescriptor(BaseDescriptor):
    def __init__(self, name, precision, signed, scale, ttl=60):
        super().__init__(name, ttl)
        self.resolution = Decimal(10) ** -precision
        self.signed = signed
        self.scale = scale

    def convert(self, data):
        int_value = int.from_bytes(data, byteorder="little", signed=self.signed)
        return Decimal(int_value).scaleb(self.scale).quantize(self.resolution)

    def equals(self, new, old):
        return not abs(new - old) > self.resolution


class Device(UserDict):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.cache = {}
        self.timestamp = {}

    def clear(self):
        for l in [k for k in self]:
            self.__delattr__(l)


class DevicesDict(UserDict):
    def __init__(self, factory):
        super().__init__(self)
        self.factory = factory

    def __missing__(self, key):
        self.data[key] = self.factory(mac_address=key)
        return self.data[key]

