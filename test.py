from compose import struct, Provider, mkmeth, structs
from collections import abc
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
