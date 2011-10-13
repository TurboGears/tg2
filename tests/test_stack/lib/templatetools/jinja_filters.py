try:
    from hashlib import sha1
except ImportError:
    from sha1 import sha1

# avoid polluting module namespace
__all__ = ['codify']

def codify(value):
    string_hash = sha1(value)
    return string_hash.hexdigest()

