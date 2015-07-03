from tg import jsonify, lurl
from datetime import datetime
from decimal import Decimal
from nose.tools import raises
from nose import SkipTest
from webob.multidict import MultiDict
import json
from tg.util import LazyString
from tg.util.webtest import test_context


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
    d = list(range(3))
    encoded = jsonify.encode_iter(d)
    assert ''.join(jsonify.encode_iter(d)) == jsonify.encode(d)

def test_dictionary():
    d = {'a': 1, 'b': 2}
    encoded = jsonify.encode(d)
    expected = json.dumps(json.loads('{"a": 1, "b": 2}'))
    assert encoded == expected

@raises(jsonify.JsonEncodeError)
def test_nospecificjson():
    b = Baz()
    try:
        encoded = jsonify.encode(b)
    except TypeError as e:
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

def test_datetime():
    d = datetime.utcnow()
    encoded = jsonify.encode({'date':d})
    assert str(d.year) in encoded, (str(d), encoded)

def test_datetime_iso():
    isodates_encoder = jsonify.JSONEncoder(isodates=True)

    d = datetime.utcnow()
    encoded = jsonify.encode({'date': d}, encoder=isodates_encoder)

    isoformat_without_millis = json.dumps({'date': d.isoformat()[:19]})
    assert isoformat_without_millis == encoded, (isoformat_without_millis, encoded)
    assert 'T' in encoded, encoded

def test_date_iso():
    isodates_encoder = jsonify.JSONEncoder(isodates=True)

    d = datetime.utcnow().date()
    encoded = jsonify.encode({'date': d}, encoder=isodates_encoder)

    isoformat_without_millis = json.dumps({'date': d.isoformat()})
    assert isoformat_without_millis == encoded, (isoformat_without_millis, encoded)

    loaded_date = json.loads(encoded)
    assert len(loaded_date['date'].split('-')) == 3

def test_decimal():
    d = Decimal('3.14')
    encoded = jsonify.encode({'dec':d})
    assert '3.14' in encoded

def test_objectid():
    try:
        from bson import ObjectId
    except:
        raise SkipTest()

    d = ObjectId('507f1f77bcf86cd799439011')
    encoded = jsonify.encode({'oid':d})
    assert encoded == '{"oid": "%s"}' % d, encoded

def test_multidict():
    d = MultiDict({'v':1})
    encoded = jsonify.encode({'md':d})
    assert encoded == '{"md": {"v": 1}}', encoded

def test_json_encode_lazy_url():
    with test_context(None, '/'):
        url = lurl('/test')
        encoded = jsonify.encode({'url': url})
        assert encoded == '{"url": "/test"}', encoded

def test_json_encode_lazy_string():
    text = LazyString(lambda: 'TEST_STRING')
    encoded = jsonify.encode({'text': text})
    assert encoded == '{"text": "TEST_STRING"}', encoded

def test_json_encode_generators():
    encoded = jsonify.encode({'values': (v for v in [1, 2, 3])})
    assert encoded == '{"values": [1, 2, 3]}', encoded