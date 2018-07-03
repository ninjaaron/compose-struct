compose
=======
yet another namedtuple alternative for Python

``compose.struct`` is something like an alternative to namedtuple
attrs_ and now dataclasses_ in Python 3.7.

.. _attrs: https://github.com/python-attrs/attrs
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

You can, naturally, implement any other methods you wish.

How's this different from attrs_ and dataclasses_? A few ways. Aside
from the use of ellipsis to create positional parameters, another that
can be seen here is that everything is based on ``__slots__``, which
means your attribute lookup will be faster and your instances more
compact in memory. attrs_ allows you to use slots, but ``struct``
defaults to using slots. This means that attributes cannot be
dynamically created. If a class needs private attributes, you may
define additional slots with the usual method of defining
``__slots__`` inside the class body.

Another important distinction is ``compose.struct`` doesn't define a
bunch of random dunder methods. You get your ``__init__`` method and
your ``__repr__`` and that's it. It is the opinion of the author that
sticking all attributes in a tuple and comparing them usually is *not*
what you want when defining a new type. However, it is still easy to get
more dunder methods, as you will see in the following section.

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
given as an argument to Provides. The following code is more or less
equivalent to subclassing ``collections.UserList``, but no inheritance
is used.

.. code:: Python

  from collections import abc

  @struct
  class ListWrapper:
      self.data = Provider(abc.MutableSequence)
      self.metadata = None

An instances of this class tested with ``isinstance(instance,
abc.MutableSequence)`` will return ``True`` because wrapper methods
have been generated on ``self.data`` for all the methods
``abc.MutableSequence``. Note that ``abc.MutableSequence`` does not
actually provide all of the methods a real list does. If you want ALL
of them, you can use ``Provides(list)``.

Note that you cannot implicitly make pass-through methods for
``__setattr__`` and ``__getattribute__``, since they have some rather
strange behaviors. You can, however, pass them explicitly to
``Provider`` to force the issue. In the case of ``__setattr__``, This
invokes special behavior. See `__setattr__ hacks`_ for
details.

All methods defined with a provider can be overridden in the body of the
class as desired. Methods can also be overridden by other providers.
It's first-come, first-serve in that case. The Provider you want to
define the methods has to be placed *above* any other interfaces that
implement the same method.

You can use ``@struct(frozen=True)`` to make your class more-or-less
immutable after it initializes. It will raise an exception if you try
to change it using the normal means.

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

Also be aware that this library uses code generation at class-creation
time. The intent is to optimize performance of instances at the cost
of slowing class creation. If you're dynamically creating huge numbers
of classes, using ``compose.struct`` might be a bad idea. FYI,
``namedtuple`` does the same. I haven't looke at the source for attrs_
too much, but I did see some strings with sourcecode there as well.

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

__setattr__ hacks
-----------------
 If you choose to create an attribute
wrapper for ``__setattr__``, the default will look like this so you
won't hit a recursion error while accessing pre-defined attributes:

.. code:: Python

    def __setattr__(self, attribute, value):
        if attr in self.__slots__:
            object.__setattr__(self, attribute, value)
        else:
            setattr(self.{wrapped_attribute}, attribute, value)

If you want to override ``__setattr__`` with a more, eh, "exotic"
method, you may want to build your struct with the ``escape_setattr``
argument.

.. code:: Python

    @struct(escape_setattr=True)
    class Foo:
         bar = ...
         baz = ...

     def __setattr__(self, attribute, value):
          setattr(self.bar, attribute, value)

This allows attributes to be set when the object is initialized, but
will use your method at all other times, *including in other methods,
which may break your stuff*. Definiting a ``__setattr__`` method like
this together with the default ``__getattr__`` wrapper will cause a
recursion error durring initialization of you don't use
``escape_setattr``.
