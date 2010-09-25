from tg import jsonify
from nose.tools import raises

class Foo(object):
    def __init__(self, bar):
        self.bar = bar

class Bar(object):
    def __init__(self, bar):
        self.bar = bar
    def __json__(self):
        return 'bar-%s' % self.bar

class Baz(object):
    pass

def test_string():
    d = "string"
    encoded = jsonify.encode(d)
    assert encoded == '"string"'

@raises(jsonify.JsonEncodeError)
def test_list():
    d = ['a', 1, 'b', 2]
    encoded = jsonify.encode(d)
    assert encoded == '["a", 1, "b", 2]'

@raises(jsonify.JsonEncodeError)
def test_list_iter():
    d = range(3)
    encoded = jsonify.encode_iter(d)
    assert ''.join(jsonify.encode_iter(d)) == jsonify.encode(d)

def test_dictionary():
    d = {'a': 1, 'b': 2}
    encoded = jsonify.encode(d)
    assert encoded == '{"a": 1, "b": 2}'

@raises(jsonify.JsonEncodeError)
def test_nospecificjson():
    b = Baz()
    try:
        encoded = jsonify.encode(b)
    except TypeError, e:
        pass
    assert  "is not JSON serializable" in e.message 

def test_exlicitjson():
    b = Bar("bq")
    encoded = jsonify.encode(b)
    assert encoded == '"bar-bq"'

@raises(jsonify.JsonEncodeError)
def test_exlicitjson_in_list():
    b = Bar("bq")
    d = [b]
    encoded = jsonify.encode(d)
    assert encoded == '["bar-bq"]'

def test_exlicitjson_in_dict():
    b = Bar("bq")
    d = {"b": b}
    encoded = jsonify.encode(d)
    assert encoded == '{"b": "bar-bq"}'
