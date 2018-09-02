"""Make cheap-ish datastructures based on class attributes. Similar to
dataclasses and attrs modules. It uses slots for everything.

Unlike dataclasses, it doesn't rely on type annotations.

Unlike attrs, you don't need a bunch of ugly function calls to make a
simple struct. A few are provided if you really want them.

Unlike either of them, the only free methods it gives you are __init__
and __repr__ (the latter of which is replacable). Both of these
libraries try to replace namedtuple to some degree. Like namedtuple,
they both tend to rely somewhat on tuples to provide free methods. You
can generate some methods from attributes if you like with the
`provides` function, but they aren't based on tuples of the arguments,
because, seriously, why would they be? It is the opinion of the
developer that composition is a superior way to implement free methods.

namedtuples uses code generation when the
class is created to provide some optimization at instance-creation time.
struct does this also. attrs does very little of this and dataclasses
(as far as I know) does none at all.

I leave it to potential users to decide whether this is good or bad. It
certainly is flexible. Raymond Hettinger, Armin Ronacher and the PyPy
guys all did it. What could go wrong?
"""
import functools
import inspect
from . import empty, args, kwargs
from .mkmeth import mkmethod
from .templates import add_attr, templates, interfaces, STRUCT_TEMPLATE, NL
NO_INHERIT = ('__getattribute__', '__setattr__')
DEFAULTS = {'__module__', '__qualname__', '__slots__',
            '__doc__', '__dict__', '__weakref__', '__annotations__'}


class Inheritance(Exception):
    pass


class Frozen(Exception):
    pass


class TooManyPuppies(Exception):
    pass


def _decifer_callables(cls):
    try:
        yield from ((name, None) for name in cls.__abstractmethods__)
    except AttributeError:
        pass
    for k, v in vars(cls).items():
        if callable(v) and k not in NO_INHERIT:
            yield k, v


def _unpack(arg):
    if inspect.isclass(arg):
        yield from _decifer_callables(arg)
    else:
        try:
            yield from ((name, None) for name in interfaces[arg])
        except KeyError:
            yield arg, None


class Provider:
    """This class exists only so I can can type-check for it!"""
    __slots__ = 'interfaces', 'default', 'args', 'kwargs'

    def __init__(self, *interfaces, default=empty, args=False, kwargs=False):
        self.default = default
        self.args = args
        self.kwargs = kwargs
        ifaces = []
        for inf in interfaces:
            if inf is args:
                self.args = True
            elif inf is kwargs:
                self.kwargs = True
            else:
                ifaces.append(inf)
        self.interfaces = ifaces

    def __iter__(self):
        for arg in self.interfaces:
            yield from _unpack(arg)


def struct_repr(self):
    name = self.__class__.__name__
    sig = inspect.signature(self.__class__)
    attributes_str = ['%s=%r' % (p.name, getattr(self, k))
                      for k, p in sig.parameters.items()]
    return '%s(%s)' % (name, ', '.join(attributes_str))


def to_dict(self):
    sig = inspect.signature(self.__class__)
    return {p.name: getattr(self, k) for k, p in sig.parameters.items()}


def mkclass(vals):
    ns = {}
    try:
        exec(STRUCT_TEMPLATE.format(**vals), ns)
    except Exception:
        print(STRUCT_TEMPLATE.format(**vals))
        raise
    return ns[vals['name']]


def getmethod(attr, name, func=None):
    try:
        code = add_attr(templates[name], attr)
    except KeyError:
        name, code = mkmethod(attr, name)

    ns = {}
    try:
        exec(code, ns)
    except Exception:
        print(code)
        raise
    return ns[name]


def compose(cls, providers):
    for attr, provider in providers:
        for name, meth in provider:
            if not hasattr(cls, name) or name in NO_INHERIT:
                setattr(cls, name, getmethod(attr, name))


def sort_types(dct):
    __slots__ = list(dct.get('__slots__') or [])

    args_ = []
    kwargs_ = {}
    callables = {}
    providers = []
    starargs = None
    starkwargs = None
    annotations = dct.get('__annotations__', {})
    for k, v in dct.items():
        if k in DEFAULTS:
            continue
        elif v is ...:
            args_.append(k)
        elif isinstance(v, Provider):
            providers.append((k, v))
            if v.default is empty:
                if v.args:
                    starargs = k
                elif v.kwargs:
                    starkwargs = k
                elif k not in annotations:
                    args_.append(k)
            else:
                kwargs_[k] = v.default
        elif v is args:
            starargs = k
        elif v is kwargs:
            starkwargs = k
        elif callable(v) or isinstance(v, (classmethod, property)):
            callables[k] = v
        elif k not in __slots__:
            kwargs_[k] = v

    if annotations:
        newargs = [a for a in annotations if a not in kwargs_]
        args_ = newargs + args_

    return (__slots__, args_, kwargs_, starargs,
            starkwargs, callables, providers)


def frozen_setattr(self, attr, value):
    raise Frozen(self.__class__.__name__ + ' type is immutable... -ish.')


def struct(cls=None, escape_setattr=False, frozen=False):
    if not cls:
        return functools.partial(
            struct, escape_setattr=escape_setattr, frozen=frozen)
    # get some interesting data
    dct = cls.__dict__
    name = cls.__name__
    doc = cls.__doc__
    annotations = getattr(cls, '__annotations__', None)
    if len(cls.__bases__) > 1 or cls.__base__ != object:
        raise Inheritance('structs are not allowed to inherit. use the '
                          '`provide` function for composition or use an '
                          'register with an abstract base class (see abc '
                          'module.)')
    (__slots__, args, kwargs, starargs,
     starkwargs, callables, providers) = sort_types(dct)

    # build string values to put in the template
    vals = {
        'name': name,
        'args': (', %s' % ', '.join(args)) if args else '',
        'starargs': (', *%s' % starargs if starargs else ''),
        'kwargs': (
            ', %s' % ', '.join('%s=%r' % (k, v) for k, v in kwargs.items())
            if kwargs else ''),
        'starkwargs': (', **%s' % starkwargs if starkwargs else ''),
    }
    args.extend(kwargs)
    if starargs:
        args.append(starargs)
    if starkwargs:
        args.append(starkwargs)
    if escape_setattr or frozen:
        temp = 'object.__setattr__(self, {0!r}, {0})'
    else:
        temp = 'self.{0} = {0}'
    vals['init_body'] = NL.join(temp.format(a)
                                for a in args)
    if '_init' in callables:
        vals['init_body'] += NL + 'self._init()'
    __slots__.extend(args)
    vals['slots'] = __slots__

    # make the new class
    cls = mkclass(vals)

    # tack on the rest of the attributes.
    if annotations:
        cls.__init__.__annotations__ = annotations
    if '__repr__' not in dct:
        cls.__repr__ = struct_repr
    if 'to_dict' not in dct:
        cls.to_dict = to_dict
    cls.__slots__ = __slots__
    cls.__doc__ = doc
    for k, v in callables.items():
        setattr(cls, k, v)
    if frozen:
        cls.__setattr__ = frozen_setattr
    compose(cls, providers)
    return cls
