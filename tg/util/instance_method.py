def im_func(f):
    return getattr(f, "__func__", None)


def default_im_func(f):
    return getattr(f, "__func__", f)


def im_self(f):
    return getattr(f, "__self__", None)


def im_class(f):
    self = im_self(f)
    if self is not None:
        return self.__class__
    else:
        return None
