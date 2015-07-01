class LazyString(object):
    """Behaves like a string, but no instance is created until the string is actually used.

    Takes a function which should be a string factory and a set of arguments to pass
    to the factory. Whenever the string is accessed or manipulated the factory is called
    to create the actual string. This is used mostly by lazy internationalization.

    """
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def eval(self):
        return self.func(*self.args, **self.kwargs)

    def __unicode__(self):
        return unicode(self.eval())

    def __str__(self):
        return str(self.eval())

    def __mod__(self, other):
        return self.eval() % other

    def __getattr__(self, attr):
        return getattr(self.eval(), attr)

    def __json__(self):
        return str(self)


def lazify(func):
    """Decorator to return a lazy-evaluated version of the original

    Applying decorator to a function it will create a :class:`.LazyString`
    with the decorated function as factory.

    """
    def newfunc(*args, **kwargs):
        return LazyString(func, *args, **kwargs)
    newfunc.__name__ = 'lazy_%s' % func.__name__
    newfunc.__doc__ = 'Lazy-evaluated version of the %s function\n\n%s' % \
        (func.__name__, func.__doc__)
    return newfunc
