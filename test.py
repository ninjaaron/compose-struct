from compose import struct, Provider, mkmeth, args, kwargs
from collections import abc
import typing as t
real_mkmeth = mkmeth.mkmethod


def mkmethod(*args, **kwargs):
    n, c = real_mkmeth(*args, **kwargs)
    print(c)
    return c


mkmeth.mkmethod = mkmethod
l = ['spam', 'eggs', 'dog', 'cat']


def mkclass(*provides):

    @struct
    class SomeClass:
        data = Provider(*provides)
        metadata = None

    return SomeClass

@struct
class LinkedList:
    head: t.Any
    tail: 'LinkedList' = None

    @classmethod
    def new(cls, items: t.Iterable) -> 'LinkedList':
        node = None
        for item in reversed(items):
            node = cls(item, node)
        return node

    def __iter__(self):
        node = self
        while node:
            yield node.head
            node = node.tail

    def __repr__(self):
        name = self.__class__.__name__
        return '%s.new(%r)' % (name, tuple(self))

    def __radd__(self, other) -> 'LinkedList':
        return self.__class__(other, self)
