import datetime
import json

import pytest

from tg import jsonify

try:
    try:
        import sqlite3
    except:
        import pysqlite2
    from sqlalchemy import (
        Column,
        Date,
        DateTime,
        ForeignKey,
        Integer,
        MetaData,
        String,
        Table,
        Time,
        create_engine,
    )
    from sqlalchemy.orm import Session, mapper, registry, relationship

    engine = create_engine("sqlite:///:memory:")
    mapper_registry = registry()
    metadata = mapper_registry.metadata

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

    test5 = Table('test5', metadata,
        Column('id', Integer, primary_key=True),
        Column('val', String(8)),
        Column('date', DateTime()),
        Column('time', Time()))

    metadata.create_all(engine)

    class MTest2(object):
        pass
    mapper_registry.map_imperatively(MTest2, test2)

    class MTest1(object):
        pass
    mapper_registry.map_imperatively(MTest1, test1, properties={'test2s': relationship(MTest2)})

    class MTest3(object):
        def __json__(self):
            return {'id': self.id, 'val': self.val, 'customized': True}
    mapper_registry.map_imperatively(MTest3, test3)

    class MTest4(object):
        pass
    mapper_registry.map_imperatively(MTest4, test4)

    class MTest5(object):
        pass
    mapper_registry.map_imperatively(MTest5, test5)

    connection = engine.connect()
    connection.execute(test1.insert(), {'id': 1, 'val': 'bob'})
    connection.execute(test2.insert(), {'id': 1, 'test1id': 1, 'val': 'fred'})
    connection.execute(test2.insert(), {'id': 2, 'test1id': 1, 'val': 'alice'})
    connection.execute(test3.insert(), {'id': 1, 'val': 'bob'})
    connection.execute(test4.insert(), {'id': 1, 'val': 'alberto'})
    connection.execute(test5.insert(), {'id': 1, 'val': 'sometime', 'time': datetime.time(21, 20, 19),
                                        'date': datetime.datetime(2016, 12, 11, 10, 9, 8)})
except ImportError:
    from warnings import warn
    warn('SQLAlchemy or PySqlite not installed - cannot run these tests.')
else:
    def teardown_module():
        connection.close()

    def test_saobj():
        s = Session(engine)
        t = s.get(MTest1, 1)
        assert t
        encoded = jsonify.encode(t)
        expected = json.loads('{"id": 1, "val": "bob"}')
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_salist():
        s = Session(engine)
        t = s.get(MTest1, 1)
        encoded = jsonify.encode(dict(results=t.test2s))
        expected = json.loads('''{"results": [{"test1id": 1, "id": 1, "val": "fred"}, {"test1id": 1, "id": 2, "val": "alice"}]}''')
        result = json.loads(encoded)
        assert result == expected, encoded
        
    def test_select_row():
        s = Session(engine)
        t = connection.execute(test1.select())
        encoded = jsonify.encode(dict(results=t))
        expected = json.loads("""{"results": {"count": -1, "rows": [{"count": 1, "rows": {"id": 1, "val": "bob"}}]}}""")
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_select_rows():
        s = Session(engine)
        t = connection.execute(test2.select())
        encoded = jsonify.encode(dict(results=t))
        expected = json.loads("""{"results": {"count": -1, "rows": [{"count": 1, "rows": {"test1id": 1, "id": 1, "val": "fred"}}, {"count": 1, "rows": {"test1id": 1, "id": 2, "val": "alice"}}]}}""")
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_explicit_saobj():
        s = Session(engine)
        t = s.get(MTest3, 1)
        encoded = jsonify.encode(t)
        expected = json.loads('{"id": 1, "val": "bob", "customized": true}')
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_detached_saobj():
        s = Session(engine)
        t = s.get(MTest1, 1)
        # ensure it can be serialized now
        jsonify.encode(t)
        s.expunge(t)

        with pytest.raises(ValueError):
            jsonify.encode(t)

    def test_select_rows_datetime():
        s = Session(engine)
        t = connection.execute(test5.select())
        encoded = jsonify.encode(dict(results=t), encoder=jsonify.JSONEncoder(isodates=True))
        expected = """{"results": {"count": -1, "rows": [{"count": 1, "rows": {"date": "2016-12-11T10:09:08", "id": 1, "val": "sometime", "time": "21:20:19"}}]}}"""
        encoded = json.loads(encoded)
        expected = json.loads(expected)
        assert encoded == expected, encoded
