"""I try to obfuscate the fact that I'm generating sourcecode with string
templates at least a little bit. I at least feel a little shame. This is
where all the strings live.
"""
from .mkmeth import trunc_source, update_template
STRUCT_TEMPLATE = '''\
class {name}:
    __slots__ = {slots}
    def __init__(self{args}{starargs}{kwargs}{starkwargs}):
        {init_body}

'''
INIT_TEMPLATE = '''\
def __init__(self{args}{starargs}{kwargs}{starkwargs}):
    {init_body}
'''
INDENT = ' ' * 4
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


# this is going to get... a little strange.
# @trunc_source turns this class into a dictionary containing the
# sourcecode of its methods.
@trunc_source
class templates:
    def __getitem__(self, index): return self.attr[index]
    def __setitem__(self, index, value): self.attr[index] = value
    def __delitem__(self, index): del self.attr[index]
    def __getattr__(self, attr): return getattr(self.attr, attr)
    def __setattr__(self, attr, value):
        try:
            object.__setattr__(self, attr, value)
        except AttributeError:
            setattr(self.attr, attr, value)
    def __get__(self): return self.attr
    def __set__(self, val): self.attr = val
    def __add__(self, other): return self.attr + other
    def __radd__(self, other): return other + self.attr
    def __iadd__(self, other): self.attr += other
    def __pos__(self): return + self.attr
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
del op_temp, add, radd, iadd, ops, ns, iter_fn, func, op, name


def add_attr(template, attr):
    return template.replace('self.attr', 'self.' + attr)
