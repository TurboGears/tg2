from nose.tools import raises
from tg import jsonify
import json

try:
    try:
        import sqlite3
    except:
        import pysqlite2
    from sqlalchemy import (MetaData, Table, Column, ForeignKey,
        Integer, String)
    from sqlalchemy.orm import create_session, mapper, relation

    metadata = MetaData('sqlite:///:memory:')

    test1 = Table('test1', metadata,
        Column('id', Integer, primary_key=True),
        Column('val', String(8)))

    test2 = Table('test2', metadata,
        Column('id', Integer, primary_key=True),
        Column('test1id', Integer, ForeignKey('test1.id')),
        Column('val', String(8)))

    test3 = Table('test3', metadata,
        Column('id', Integer, primary_key=True),
        Column('val', String(8)))

    test4 = Table('test4', metadata,
        Column('id', Integer, primary_key=True),
        Column('val', String(8)))

    metadata.create_all()

    class Test2(object):
        pass
    mapper(Test2, test2)

    class Test1(object):
        pass
    mapper(Test1, test1, properties={'test2s': relation(Test2)})

    class Test3(object):
        def __json__(self):
            return {'id': self.id, 'val': self.val, 'customized': True}

    mapper(Test3, test3)

    class Test4(object):
        pass
    mapper(Test4, test4)

    test1.insert().execute({'id': 1, 'val': 'bob'})
    test2.insert().execute({'id': 1, 'test1id': 1, 'val': 'fred'})
    test2.insert().execute({'id': 2, 'test1id': 1, 'val': 'alice'})
    test3.insert().execute({'id': 1, 'val': 'bob'})
    test4.insert().execute({'id': 1, 'val': 'alberto'})

except ImportError:
    from warnings import warn
    warn('SQLAlchemy or PySqlite not installed - cannot run these tests.')

else:

    def test_saobj():
        s = create_session()
        t = s.query(Test1).get(1)
        encoded = jsonify.encode(t)
        expected = json.loads('{"id": 1, "val": "bob"}')
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_salist():
        s = create_session()
        t = s.query(Test1).get(1)
        encoded = jsonify.encode(dict(results=t.test2s))
        expected = json.loads('''{"results": [{"test1id": 1, "id": 1, "val": "fred"}, {"test1id": 1, "id": 2, "val": "alice"}]}''')
        result = json.loads(encoded)
        assert result == expected, encoded
        
    def test_select_row():
        s = create_session()
        t = test1.select().execute()
        encoded = jsonify.encode(dict(results=t))
        expected = json.loads("""{"results": {"count": -1, "rows": [{"count": 1, "rows": {"id": 1, "val": "bob"}}]}}""")
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_select_rows():
        s = create_session()
        t = test2.select().execute()
        encoded = jsonify.encode(dict(results=t))
        expected = json.loads("""{"results": {"count": -1, "rows": [{"count": 1, "rows": {"test1id": 1, "id": 1, "val": "fred"}}, {"count": 1, "rows": {"test1id": 1, "id": 2, "val": "alice"}}]}}""")
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_explicit_saobj():
        s = create_session()
        t = s.query(Test3).get(1)
        encoded = jsonify.encode(t)
        expected = json.loads('{"id": 1, "val": "bob", "customized": true}')
        result = json.loads(encoded)
        assert result == expected, encoded

