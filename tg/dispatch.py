from paste import httpexceptions

def object_dispatch(obj, url_path):
    remainder = url_path
    notfound_handlers = []
    while True:
        try:
            obj, remainder = find_object(obj, remainder, notfound_handlers)
            return obj, remainder
        except httpexceptions.HTTPNotFound, err:
            if not notfound_handlers: raise
            name, obj, remainder = notfound_handlers.pop()
            if name == 'default': return obj, remainder
            else:
                obj, remainder = obj(*remainder)
                continue

def find_object(obj, remainder, notfound_handlers):
    while True:
        if obj is None: raise httpexceptions.HTTPNotFound()
        if iscontroller(obj): return obj, remainder

        if not remainder or remainder == ['']:
            index = getattr(obj, 'index', None)
            if iscontroller(index): return index, remainder

        default = getattr(obj, 'default', None)
        if iscontroller(default):
            notfound_handlers.append(('default', default, remainder))

        lookup = getattr(obj, 'lookup', None)
        if iscontroller(lookup):
            notfound_handlers.append(('lookup', lookup, remainder))

        if not remainder: raise httpexceptions.HTTPNotFound()
        obj = getattr(obj, remainder[0], None)
        remainder = remainder[1:]
    
            
def iscontroller(obj):
    if not hasattr(obj, '__call__'): return False
    if not hasattr(obj, 'tg_info'): return False
    return obj.tg_info.exposed



