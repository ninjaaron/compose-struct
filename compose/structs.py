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
from . import empty
from .mkmeth import mkmethod
STRUCT_TEMPLATE = '''\
class {name}:
    __slots__ = {slots}
    def __init__(self{args}{kwargs}):
        {init_body}

'''
NO_INHERIT = ('__getattribute__', '__setattr__')

DEFAULTS = {'__module__', '__qualname__', '__slots__',
            '__doc__', '__dict__', '__weakref__', '__annotations__'}
INDENT = ' ' * 8
NL = '\n' + INDENT
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


def get_templates():
    # this is going to get... a little strange.
    from .mkmeth import trunc_source, update_template

    @trunc_source
    class templates:
        def __getitem__(self, index): return self.attr[index]
        def __setitem__(self, index, value): self.attr[index] = value
        def __delitem__(self, index): del self.attr[index]
        def __getattr__(self, attr): return getattr(self.attr, attr)
        def __setattr__(self, attr, value):
            if attr in self.__slots__:
                object.__setattr__(self, attr, value)
            else:
                setattr(self.attr, attr, value)
        def __get__(self): return self.attr
        def __set__(self, val): self.attr = val
        def __add__(self, other): return self.attr + other
        def __radd__(self, other): return other + self.attr
        def __iadd__(self, other): self.attr += other
        def __pos__(self): return +self.attr
        def __iter__(self): return iter(self.attr)

    def op_temp(temp, name, op):
        return update_template(temp, '__%s__' % name, ('+', op),
                               temps_dict=templates)

    add = templates['__add__']
    radd = templates['__radd__']
    iadd = templates['__iadd__']
    ops = '- * @ / // % ** << >> & ^ |'.split()
    ns = 'sub mul matmul truediv floordiv mod pow lshift rshift and xor or'\
        .split()
    for op, name in zip(ops, ns):
        op_temp(add, name, op)
        op_temp(radd, 'r'+name, op)
        op_temp(iadd, 'i'+name, op)
    ops = '== != > < >= <='.split()
    ns = 'eq ne gt lt ge le'.split()
    for op, name in zip(ops, ns):
        op_temp(add, name, op)
    op_temp(radd, 'contains', 'in')
    op_temp(templates['__pos__'], 'neg', '-')
    op_temp(templates['__pos__'], 'invert', '~')
    iter_fn = templates['__iter__']
    for func in ('repr str bytes hash dir bool reversed len iter abs '
                 'complex int float').split():
        update_template(iter_fn, '__%s__' % func, ('iter', func),
                        temps_dict=templates)
    return templates


templates = get_templates()


class Inheritance(Exception):
    pass


def add_attr(template, attr):
    return template.replace('self.attr', 'self.' + attr)


def _decifer_callables(cls):
    try:
        yield from ((name, None) for name in cls.__abstractmethods__)
    except AttributeError:
        pass
    for k, v in cls.__dict__.items():
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
    __slots__ = 'args', 'default'

    def __init__(self, *args, default=empty):
        self.args = args
        self.default = default

    def __iter__(self):
        for arg in self.args:
            yield from _unpack(arg)


def struct_repr(self):
    name = self.__class__.__name__
    sig = inspect.signature(self.__class__)
    attributes_str = ('%s=%r' % (n, getattr(self, n)) for n in sig.parameters)
    return '%s(%s)' % (name, ', '.join(attributes_str))


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

    args = []
    kwargs = []
    callables = {}
    providers = []
    for k, v in dct.items():
        if k in DEFAULTS:
            continue
        elif v is ...:
            args.append(k)
        elif isinstance(v, Provider):
            providers.append((k, v))
            if v.default is empty:
                args.append(k)
            else:
                kwargs.append((k, v.default))
        elif callable(v) or isinstance(v, (classmethod, property)):
            callables[k] = v
        elif k not in __slots__:
            kwargs.append((k, v))

    return __slots__, args, kwargs, callables, providers


class Frozen(Exception):
    pass


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
    if len(cls.__bases__) > 1 or cls.__base__ != object:
        raise Inheritance('structs are not allowed to inherit. use the '
                          '`provide` function for composition or use an '
                          'register with an abstract base class (see abc '
                          'module.)')
    __slots__, args, kwargs, callables, providers = sort_types(dct)

    # build string values to put in the template
    vals = {
        'name': name,
        'args': (', %s' % ', '.join(args)) if args else '',
        'kwargs': (
            ', %s' % ', '.join('%s=%r' % (k, v) for k, v in kwargs)
            if kwargs else '')
    }
    args.extend(kw[0] for kw in kwargs)
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

    # exec the template in its own namespace and get the resulting class
    cls = mkclass(vals)

    # tack on the rest of the attributes.
    if '__repr__' not in dct:
        cls.__repr__ = struct_repr
    cls.__slots__ = __slots__
    cls.__doc__ = doc
    for k, v in callables.items():
        setattr(cls, k, v)
    if frozen:
        cls.__setattr__ = frozen_setattr
    compose(cls, providers)
    return cls
