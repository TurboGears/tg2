import json

import pytest

from tests.test_stack import TestConfig, app_from_config
from tg import json_encode
from tg.support.paginate import Page
from tg.util.urls import _urlencode
from tg.util.webtest import test_context


def setup_noDB():
    base_config = TestConfig(folder='rendering',
            values={
                'use_sqlalchemy': False,
                'use_toscawidgets': False,
                'use_toscawidgets2': False
            })
    return app_from_config(base_config)


_pager = ('<div id="pager"><span class="pager_curpage">1</span>'
    ' <a href="%(url)s?page=2">2</a>'
    ' <a href="%(url)s?page=3">3</a>'
    ' <span class="pager_dotdot">..</span>'
    ' <a href="%(url)s?page=5">5</a></div>')

_data = '<ul id="data">%s</ul>' % ''.join(
        '<li>%d</li>' % i for i in range(10))


class TestPagination:
    def setup_method(self):
        self.app = setup_noDB()

    def test_basic_pagination(self):
        url = '/paginated/42'
        page = self.app.get(url)
        assert _pager % locals() in page, page
        assert _data in page, page
        url = '/paginated/42?page=2'
        page = self.app.get(url)
        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page

    def test_pagination_negative(self):
        url = '/paginated/42?page=-1'
        page = self.app.get(url)
        assert '<li>0</li>' in page

    def test_pagination_items_per_page(self):
        url = '/paginated/42?items_per_page=20'
        page = self.app.get(url)
        assert '<li>0</li>' in page
        assert '<li>19</li>' in page

    def test_pagination_items_per_page_negative(self):
        url = '/paginated/42?items_per_page=-1'
        page = self.app.get(url)
        assert '<li>0</li>' in page
        assert '<li>10</li>' not in page

    def test_pagination_non_paginable(self):
        url = '/paginated_text'
        page = self.app.get(url)
        assert 'Some Text' in page

    def test_pagination_with_validation(self):
        url = '/paginated_validated/42'
        page = self.app.get(url)
        assert _pager % locals() in page, page
        assert _data in page, page
        url = '/paginated_validated/42?page=2'
        page = self.app.get(url)
        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page

    def test_validation_with_pagination(self):
        url = '/validated_paginated/42'
        page = self.app.get(url)
        assert _pager % locals() in page, page
        assert _data in page, page
        url = '/validated_paginated/42?page=2'
        page = self.app.get(url)
        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page

    def test_pagination_with_link_args(self):
        url = '/paginate_with_params/42'
        page = self.app.get(url)
        assert 'param1=hi' in page
        assert 'param2=man' in page
        assert 'partial' not in page
        assert '/fake_url' in page
        url = '/paginate_with_params/42?page=2'
        page = self.app.get(url)
        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page

    def test_multiple_paginators(self):
        url = '/multiple_paginators/42'

        try:
            from collections import OrderedDict
            params = (('testdata_page', 2), ('testdata2_page', 2))
            reverse_params = OrderedDict(reversed(params))
            params = OrderedDict(params)
        except ImportError:
            reverse_params = params = {'testdata2_page': 2, 'testdata_page': 2}

        goto_page2_link = url + '?' + _urlencode(params)
        goto_page2_reverse_link = url + '?' + _urlencode(reverse_params)

        page = self.app.get(url)
        assert '/multiple_paginators/42?testdata2_page=2' in page, str(page)
        assert '/multiple_paginators/42?testdata_page=2' in page, str(page)

        url = '/multiple_paginators/42?testdata_page=2'
        page = self.app.get(url)

        assert (
            goto_page2_link in page or goto_page2_reverse_link in page
        ), str(page)
        assert '/multiple_paginators/42?testdata_page=4' in page, str(page)

        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page
        assert '<li>142</li>' in page
        assert '<li>151</li>' in page

        url = '/multiple_paginators/42?testdata2_page=2'
        page = self.app.get(url)

        assert (
            goto_page2_link in page or goto_page2_reverse_link in page
        ), str(page)
        assert '/multiple_paginators/42?testdata2_page=4' in page, str(page)

        assert '<li>0</li>' in page
        assert '<li>9</li>' in page
        assert '<li>151</li>' not in page
        assert '<li>161</li>' in page

    def test_json_pagination(self):
        url = '/paginated/42.json'
        page = self.app.get(url)
        assert '[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]' in page

        url = '/paginated/42.json?page=2'
        page = self.app.get(url)
        assert '[10, 11, 12, 13, 14, 15, 16, 17, 18, 19]' in page


class TestPage(object):
    def test_not_a_number_page(self):
        p = Page(range(100), items_per_page=10, page='A')
        sec = list(p)
        assert sec[-1] == 9, sec

    def test_empty_list(self):
        p = Page([], items_per_page=10, page=1)
        assert list(p) == []

    def test_page_out_of_bound(self):
        p = Page(range(100), items_per_page=10, page=10000)
        sec = list(p)
        assert sec[-1] == 99, sec

    def test_page_out_of_lower_bound(self):
        p = Page(range(100), items_per_page=10, page=-5)
        sec = list(p)
        assert sec[-1] == 9, sec

    def test_navigator_one_page(self):
        with test_context(None, '/'):
            p = Page(range(10), items_per_page=10, page=10)
            assert p.pager() == ''

    def test_navigator_middle_page(self):
        with test_context(None, '/'):
            p = Page(range(100), items_per_page=10, page=5)
            pager = p.pager()

            assert '?page=1' in pager
            assert '?page=4' in pager
            assert '?page=6' in pager
            assert '?page=10' in pager

    def test_navigator_ajax(self):
        with test_context(None, '/'):
            p = Page(range(100), items_per_page=10, page=5)
            pager = p.pager(onclick='goto($page)')

            assert 'goto(1)' in pager
            assert 'goto(4)' in pager
            assert 'goto(6)' in pager
            assert 'goto(10)' in pager


try:
    pass
except:
    pass
from sqlalchemy import Column, ForeignKey, Integer, String, Table, create_engine
from sqlalchemy.orm import Session as SQLASession
from sqlalchemy.orm import registry, relationship

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

metadata.create_all(engine)

class MTest2(object):
    pass
mapper_registry.map_imperatively(MTest2, test2)

class MTest1(object):
    pass
mapper_registry.map_imperatively(MTest1, test1, properties={'test2s': relationship(MTest2)})

class MTest3(object):
    pass
mapper_registry.map_imperatively(MTest3, test3)

class MTest4(object):
    pass
mapper_registry.map_imperatively(MTest4, test4)

connection = engine.connect()
connection.execute(test1.insert(), {'id': 1, 'val': 'bob'})
connection.execute(test2.insert(), {'id': 1, 'test1id': 1, 'val': 'fred'})
connection.execute(test2.insert(), {'id': 2, 'test1id': 1, 'val': 'alice'})
connection.execute(test3.insert(), {'id': 1, 'val': 'bob'})
connection.execute(test4.insert(), {'id': 1, 'val': 'alberto'})

def teardown_module():
    connection.close()

class TestPageSQLA(object):
    def setup_class(self):
        self.s = SQLASession(connection)

    def test_relationship(self):
        t = self.s.get(MTest1, 1)
        p = Page(t.test2s, items_per_page=1, page=1)
        assert len(list(p)) == 1
        assert list(p)[0].val == 'fred', list(p)

    def test_query(self):
        q = self.s.query(MTest2)
        p = Page(q, items_per_page=1, page=1)
        assert len(list(p)) == 1
        assert list(p)[0].val == 'fred', list(p)

    def test_json_query(self):
        q = self.s.query(MTest2)
        p = Page(q, items_per_page=1, page=1)
        res = json.loads(json_encode(p))
        assert len(res['entries']) == 1
        assert res['total'] == 2
        assert res['entries'][0]['val'] == 'fred'


try:
    import ming
    from ming import ASCENDING, Session, create_datastore, schema
    from ming.odm import (
        FieldProperty,
        ForeignIdProperty,
        Mapper,
        ODMSession,
        RelationProperty,
    )
    from ming.odm.declarative import MappedClass
except ImportError:
    ming = None


class TestPageMing(object):
    @classmethod
    def setup_class(cls):
        if ming is None:
            pytest.skip('Ming not available...')

        cls.basic_session = Session(create_datastore('mim:///testdb'))
        cls.s = ODMSession(cls.basic_session)

        class Author(MappedClass):
            class __mongometa__:
                session = cls.s
                name = 'wiki_author'

            _id = FieldProperty(schema.ObjectId)
            name = FieldProperty(str)
            pages = RelationProperty('WikiPage')

        class WikiPage(MappedClass):
            class __mongometa__:
                session = cls.s
                name = 'wiki_page'

            _id = FieldProperty(schema.ObjectId)
            title = FieldProperty(str)
            text = FieldProperty(str)
            order = FieldProperty(int)
            author_id = ForeignIdProperty(Author)
            author = RelationProperty(Author)

        cls.Author = Author
        cls.WikiPage = WikiPage
        Mapper.compile_all()

        cls.author = Author(name='author1')
        author2 = Author(name='author2')

        WikiPage(title='Hello', text='Text', order=1, author=cls.author)
        WikiPage(title='Another', text='Text', order=2, author=cls.author)
        WikiPage(title='ThirdOne', text='Text', order=3, author=author2)
        cls.s.flush()
        cls.s.clear()

    def teardown_method(self):
        self.s.clear()

    def test_query(self):
        q = self.WikiPage.query.find().sort([('order', ASCENDING)])
        p = Page(q, items_per_page=1, page=1)
        assert len(list(p)) == 1
        assert list(p)[0].title == 'Hello', list(p)

    def test_json_query(self):
        q = self.WikiPage.query.find().sort([('order', ASCENDING)])
        p = Page(q, items_per_page=1, page=1)
        res = json.loads(json_encode(p))
        assert len(res['entries']) == 1
        assert res['total'] == 3
        assert res['entries'][0]['title'] == 'Hello', res['entries']
        assert res['entries'][0]['author_id'] == str(self.author._id), res['entries']

    def test_relation(self):
        a = self.Author.query.find({'name': 'author1'}).first()
        p = Page(a.pages, items_per_page=1, page=1)
        assert len(list(p)) == 1
        assert list(p)[0].title in ('Hello', 'Another'), list(p)
