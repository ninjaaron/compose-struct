compose
=======
Yet another namedtuple alternative for Python

``compose.Struct`` is something like an alternative to namedtuple,
attrs_ and now dataclasses_ in Python 3.7.

.. _attrs: https://github.com/python-attrs/attrs
.. _dataclasses: https://docs.python.org/3/library/dataclasses.html

to create a new struct, you simply:

.. code:: Python

  
  class Foo(compose.Struct):
      bar = ...
      baz = 'spam'

This generates a class like this:

.. code:: Python

  class Foo:
      __slots__ = 'bar', 'baz'

      def __init__(self, bar, baz='spam'):
          self.bar = bar
          self.baz = baz

You can, naturally, implement any other methods you wish.

You can also use type annotation syntax for positional arguments:

.. code:: Python

  class Foo(compose.Struct):
      bar: int
      baz: str = 'spam'

If the ``name = ...`` syntax is used in combination with type annotation
syntax for positional arguments, all positional arguments with
annotations will come before positional arguments without. However, this
should be considered an implementation detail. best practice is to not
mix the two styles. Use ``typing.Any`` if you are using type
annotations and don't want one of the arguments to care about type.

How's this different from attrs_ and dataclasses_? A few ways. Aside
from the use of ellipsis to create positional parameters, another
difference that can be seen here is that everything is based on
``__slots__``, which means your attribute lookup will be faster and your
instances more compact in memory. attrs_ allows you to use slots, but
``struct`` only uses slots. This means that attributes cannot be
dynamically created. If a class needs private attributes, you may create
additional slots with the usual method of defining ``__slots__`` inside
the class body.

Another important distinction is ``compose.Struct`` doesn't define a
bunch of random dunder methods. You get your ``__init__``, ``__repr__``,
and ``to_dict`` and that's it [#]_. It is the opinion of the author that
sticking all attributes in a tuple and comparing them usually is *not*
what you want when defining a new type. However, it is still easy to get
more dunder methods, as you will see in the following section.

.. [#] OK, It actually also gives you __getstate__ and __setstate__,
       which are required for pickling objects.

Interfaces
----------
Perhaps the most significant difference between our structs and
alternatives is that we emphasize composition over inheritance. A
``struct`` isn't even able to inherit in the normal way! It's an
outrage! What about interfaces!? What about polymorphism!? Well, what
``compose`` provides is a simple way to generate pass-through methods to
attributes.

.. code:: Python

  from compose import Struct, Provider

  class ListWrapper(Struct):
      data = Provider('__getitem__', '__iter__')
      metadata = None


So this will generate pass-through methods for ``__getitem__`` and
``__iter__`` to the ``data`` attribute. Certain python keywords and
operators can be used as shorthand for adding dunder methods as well.

.. code:: Python

  @struct
  class ListWrapper:
      data = Provider('[]', 'for')
      metadata = None

Here, ``[]`` is shorthand for item access and implements
``__getitem__``, ``__setitem__`` and ``__delitem__``. ``for`` implements
the ``__iter__`` method. A full list of these abbreviations can be found
below in the `Pre-Defined Interfaces`_ section.

Going even deeper, interfaces can be specified as classes. Wrapper
methods will be created for any method attached to a class which is
given as an argument to ``Provider``. The following code is more or less
equivalent to subclassing ``collections.UserList``, but no inheritance
is used.

.. code:: Python

  from collections import abc

  class ListWrapper(Struct):
      data = Provider(abc.MutableSequence)
      metadata = None

An instances of this class tested with ``isinstance(instance,
abc.MutableSequence)`` will return ``True`` because wrapper methods
have been generated on ``self.data`` for all the methods in
``abc.MutableSequence``. *Note that ``abc.MutableSequence`` does not
actually provide all of the methods a real list does. If you want ALL
of them, you can use ``Provides(list)``.*

You cannot implicitly make pass-through methods for ``__setattr__`` and
``__getattribute__`` by passing in a class that implements them, since
they have some rather strange behaviors. You can, however, pass them
explicitly to ``Provider`` to force the issue.  In the case of
``__setattr__``, This invokes special behavior. See `__setattr__ hacks`_
for details.

All methods defined with a provider can be overridden in the body of the
class as desired. Methods can also be overridden by other providers.
It's first-come, first-serve in that case. The Provider you want to
define the methods has to be placed *above* any other interfaces that
implement the same method.

Mix-in Classes vs. Inheritance
------------------------------
There is no inheritance with Structs. Because of metaclass magic, a
class that inherits from Struct is not its child. It is always a child
of ``object``. ``Provider`` is a way to implement pass-through methods
easily. Mix-in classes bind methods from other classes directly to your
class. It doesn't go through the class hierarchy and rebind everything,
only methods defined directly on the mix-in class. Inheriting from
normal python classes may have unpredictable results.

``compose`` provides one mix-in class: ``Immutable``, which is
implemented like this:

.. code:: Python

  class Mutablility(Exception):
      pass


  class Immutable:
      def __setattr__(self, attr, value):
          raise Mutablility(
              "can't set {0}.{1}. type {0} is immutable.".format(
                  self.__class__.__name__,
                  attr,
                  value
              ))

It can be used like this:

.. code:: Python

  from compose import Struct, Immutable


  class Foo(Struct, Immutable):
      bar = ...
      baz = ...

When an instance of ``Foo`` is created, it will not be possible to set
attributes afterwards in the normal way. (Though it is technically
possible if you set it with ``object.__setattr__(instance, 'attr',
value)``). Attempting to do ``foo.bar = 7`` will raise a ``Mutability``
error.

If you need a ``struct`` to look like a child of another class, I
suggest using the abc_ module to define abstract classes. This allows
classes to look like children for the purposes of type-checking, but
without actually using inheritance.

.. _abc: https://docs.python.org/3/library/abc.html

Order
~~~~~
This is the order of priority for where methods come from:

- Struct generates a unique ``__init__`` method for each class it
  creates. This cannot be overriden. Alternative constructors should be
  implemented as class methods.
- methods defined in the body of the struct get next dibs.
- any attributes defined on your mix-ins will be defined on the class if
  they don't already exist.
- Only then are ``Provider`` attributes allowed to add any methods which
  haven't yet been defined.

``*args`` and ``**kwargs``
--------------------------
Though it is not especially recommended, it is possible to implement
``*args`` and ``**kwargs`` for your constructor.

.. code:: Python

  >>> from compose import Struct, args, kwargs
  >>> class Foo(Struct):
  ...     items = args
  ...     mapping = kwargs
  ...
  >>> f = Foo('bar', 'baz', spam='eggs')
  >>> f
  Foo(*items=('bar', 'baz'), **mapping={'spam': 'eggs'})

This breaks the principle that the object's repr can be used to
instantiate an identical instance, but it does at least give the option
and still makes the internal structure of the class transparent. With
``Provider`` parameters, simply pass in ``compose.args`` or
``compose.kwargs`` as arguments the constructor.

.. code:: Python

  >>> class MySequence(Struct):
  ...     data = Provider('__getitem__', '__iter__', args)
  ...
  >>> s = MySequence('foo', 'bar', 'baz')
  >>> s
  MySequence(*data=('foo', 'bar', 'baz'))
  >>> for i in s:
  ...     print(i)
  ...
  foo
  bar
  baz

Caveats
-------
This library uses code generation at class-creation time. The intent is
to optimize performance of instances at the cost of slowing class
creation. If you're dynamically creating huge numbers of classes, using
``compose.Struct`` might be a bad idea. FYI, ``namedtuple`` does the
same. I haven't looked at the source for attrs_ too much, but I did see
some strings with sourcecode there as well.

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
        try:
            object.__setattr__(self, attribute, value)
        except AttributeError:
            setattr(self.wrapped_attribute, attribute, value)

If you want to override ``__setattr__`` with a more, eh, "exotic"
method, the attributes defined in the class body will be set properly
when the instance is initialized, but will use your method at all other
times, *including in other methods, which may break your stuff*.
