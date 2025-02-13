import json
from decimal import Decimal

import pytest
from webob.multidict import MultiDict

from tests.base import utcnow
from tg import jsonify, lurl
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

def test_list():
    d = ['a', 1, 'b', 2]

    with pytest.raises(jsonify.JsonEncodeError):
        encoded = jsonify.encode(d)
    #assert encoded == '["a", 1, "b", 2]'

def test_list_iter():
    d = list(range(3))

    with pytest.raises(jsonify.JsonEncodeError):
        encoded = jsonify.encode_iter(d)
    #assert ''.join(jsonify.encode_iter(d)) == jsonify.encode(d)

def test_list_allowed_iter():
    lists_encoder = jsonify.JSONEncoder(allow_lists=True)
    d = list(range(3))
    encoded = jsonify.encode_iter(d, lists_encoder)
    assert ''.join(encoded) == '[0, 1, 2]'

def test_dictionary():
    d = {'a': 1, 'b': 2}
    encoded = jsonify.encode(d)
    expected = json.dumps(json.loads('{"a": 1, "b": 2}'))
    assert encoded == expected


def test_nospecificjson():
    b = Baz()

    with pytest.raises(jsonify.JsonEncodeError):
        encoded = jsonify.encode(b)

def test_exlicitjson():
    b = Bar("bq")
    encoded = jsonify.encode(b)
    assert encoded == '"bar-bq"'

def test_exlicitjson_in_list():
    b = Bar("bq")
    d = [b]
    with pytest.raises(jsonify.JsonEncodeError):
        encoded = jsonify.encode(d)

def test_exlicitjson_in_dict():
    b = Bar("bq")
    d = {"b": b}
    encoded = jsonify.encode(d)
    assert encoded == '{"b": "bar-bq"}'

def test_datetime():
    d = utcnow()
    encoded = jsonify.encode({'date':d})
    assert str(d.year) in encoded, (str(d), encoded)

def test_datetime_iso():
    isodates_encoder = jsonify.JSONEncoder(isodates=True)

    d = utcnow()
    encoded = jsonify.encode({'date': d}, encoder=isodates_encoder)

    isoformat_without_millis = json.dumps({'date': d.isoformat()[:19]})
    assert isoformat_without_millis == encoded, (isoformat_without_millis, encoded)
    assert 'T' in encoded, encoded

def test_date_iso():
    isodates_encoder = jsonify.JSONEncoder(isodates=True)

    d = utcnow().date()
    encoded = jsonify.encode({'date': d}, encoder=isodates_encoder)

    isoformat_without_millis = json.dumps({'date': d.isoformat()})
    assert isoformat_without_millis == encoded, (isoformat_without_millis, encoded)

    loaded_date = json.loads(encoded)
    assert len(loaded_date['date'].split('-')) == 3

def test_datetime_time():
    d = utcnow().time()
    encoded = jsonify.encode({'date':d})
    assert str(d.hour) in encoded, (str(d), encoded)

def test_datetime_time_iso():
    isodates_encoder = jsonify.JSONEncoder(isodates=True)

    d = utcnow().time()
    encoded = jsonify.encode({'date': d}, encoder=isodates_encoder)

    isoformat_without_millis = json.dumps({'date': d.isoformat()[:8]})
    assert isoformat_without_millis == encoded, (isoformat_without_millis, encoded)

def test_decimal():
    d = Decimal('3.14')
    encoded = jsonify.encode({'dec':d})
    assert '3.14' in encoded

def test_objectid():
    try:
        from bson import ObjectId
    except ImportError:
        raise pytest.skip("MongoDB not supported on this system")

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
