import inspect
import re
whitespace = re.compile(r'\s+')


def trunc_source(func):
    if isinstance(func, type):
        return {n: trunc_source(m) for n, m
                in func.__dict__.items() if callable(m)}

    lines = inspect.getsourcelines(func)[0]
    indent = whitespace.match(lines[0])
    if indent:
        span = indent.end()
        lines = (l[span:] for l in lines)
    return ''.join(lines)


def call_from_meth_sig(sig):
    if isinstance(sig, str):
        return sig.replace('(self, ', '(')
    parms = sig.parameters.values()
    parms = (inspect.Parameter(p.name, p.kind)
             for p in parms if p.name != 'self')
    return str(sig.replace(parameters=parms))


def mkmethod(attr, name_or_func, sig='(self, *args, **kwargs)',
             ret='return ', args=True):
    if callable(name_or_func):
        name = name_or_func.__name__
        try:
            sig = inspect.signature(name_or_func)
        except ValueError:
            pass
    else:
        name = name_or_func

    args = call_from_meth_sig(sig) if args else None
    parts = ('def ', name, str(sig), ': ', ret, 'self.', attr, '.', name, args)
    return name, ''.join(p for p in parts if p)


def update_template(temp, name, *replacements, temps_dict=None):
    temp = temp.split('(', maxsplit=1)[1]
    for string, rep in replacements:
        temp = temp.replace(string, rep)

    temp = 'def %s(%s' % (name, temp)

    if not temps_dict:
        return temp

    temps_dict[name] = temp
