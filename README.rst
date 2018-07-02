compose
=======
yet another namedtuple alternative for Python

``compose.struct`` is something like an alternative to attr.s_ and the
namedtuple and now dataclasses_ in Python 3.7

.. _attr.s: https://github.com/python-attrs/attrs
.. _dataclasses: https://docs.python.org/3/library/dataclasses.html

to create a new struct, you simply:

.. code:: Python

  @compose.struct
  class Foo:
      bar = ...
      baz = 'spam'

This generate a class like this:

.. code:: Python

  class Foo:
      __slots__ = 'bar', 'baz'

      def __init__(self, bar, baz='spam'):
          self.bar = bar
          self.baz = spam

You can, naturally implement any other methods you wish.

How's this different from attr.s_ and dataclasses_? A few ways. Aside
from the use of ellipsis to create positional parameters, another that
can be seen here is that everything is based on ``__slots__``, which
means your attribute lookup will be faster and your instances more
compact in ram. The alternatives allow you to use slots, but ``struct``
defaults to using slots. This means that attributes cannot be
dynamically created. If a class needs private attributes, you may define
additional slots with the usual method of defining ``__slots__`` inside
the class body.

Another important distinction is ``compose.struct`` doesn't define a
bunch of random dunder methods. You get your ``__init__`` method and
your ``__repr__`` and that's it. However, it is still easy to get more
dunder methods, as you will see in the following section.


Interfaces
----------
Perhaps the most significant difference our structs and alternatives is
that we emphasize composition over inheritance. A ``struct`` isn't even
able to inherit! It's an outrage! What about interfaces!? What about
polymorphism!? Well, what ``compose`` provides is a simple way to
generate pass-through methods to attributes.

.. code:: Python

  from compose import struct, Provider

  @struct
  class ListWrapper:
      self.data = Provider('__getitem__', '__iter__')
      self.metadata = None


So this will generate pass-through methods for ``__getitem__`` and
``__iter__`` to the ``data`` attribute. Certain python keywords and
operators can be used as shorthand for adding dunder methods as well.

.. code:: Python

  @struct
  class ListWrapper:
      self.data = Provider('[]', 'for')
      self.metadata = None

Here, ``[]`` is shorthand for item access and implements
``__getitem__``, ``__setitem__`` and ``__delitem__``. ``for`` implements
the ``__iter__`` method. A full list of these abbreviations can be found
below in the `Pre-Defined Interfaces`_ section.

Going even deeper, interfaces can be specified as classes. Wrapper
methods will be created for any method attached to a class which is
given as an argument to Provides. The following code is essentially
equivalent to subclassing ``collections.UserDict``, but no inheritance
is used.

.. code:: Python

  from collections import abc

  @struct
  class ListWrapper:
      self.data = Provider(abc.MutableSequence)
      self.metadata = None

An instances of this class tested with ``isinstance(instance,
abc.MutableSequence)`` will return ``True`` because wrapper methods have
been generated on ``self.data`` for all the methods
``abc.MutableSequence``.

All methods defined with a provider can be overridden in the body of the
class as desired. Methods can also be overridden by other providers.
It's first-come, first-serve in that case. The Provider you want to
define the methods has to be placed _above_ any other Interfaces that
implement the same method.

If you need a ``struct`` to look like a child of another class, I
suggest using the abc_ module to define abstract classes. This allows
classes to look like children for the purposes of type-checking, but
without actually using inheritance.

.. _abc: https://docs.python.org/3/library/abc.html

Caveats
-------
This library is still very new. As of this moment, type
annotations have not been implemented. ``*args``
and ``**kwargs`` haven't been implemented either. Both of those things
are planned. args/kwargs have a higher priority and should be available
soon.

Pre-Defined Interfaces
----------------------
This is the code that implements the expansion of interface
abbreviations for dunder methods. Any key in the ``interfaces``
dictionary may be used to implement the corresponding dunder methods on
an attribute with the ``Provides()`` constructor.

.. code:: Python

  interfaces = {
      '+': 'add radd',
      '-': 'sub rsub',
      '*': 'mul rmul',
      '@': 'matmul rmatmul',
      '/': 'truediv rtruediv',
      '//': 'floordiv rfloordiv',
      '%': 'mod rmod',
      '**': 'pow rpow',
      '<<': 'lshift rlshift',
      '>>': 'rshift rrshift',
      '&': 'and rand',
      '^': 'xor rxor',
      '|': 'or ror',
      '~': 'invert',
      '==': 'eq',
      '!=': 'ne',
      '>': 'gt',
      '<': 'lt',
      '>=': 'ge',
      '<=': 'le',
      '()': 'call',
      '[]': 'getitem setitem delitem',
      '.': 'get set delete set_name',
      'in': 'contains',
      'for': 'iter',
      'with': 'enter exit',
      'del': 'del',
      'await': 'await'
  }
  interfaces = {k: ['__%s__' % n for n in v.split()]
                for k, v in interfaces.items()}
