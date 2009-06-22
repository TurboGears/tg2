from tg.test_stack import TestConfig, app_from_config


def setup_noDB():
    base_config = TestConfig(folder='rendering',
            values={
                'use_sqlalchemy': False
            })
    return app_from_config(base_config)


class TestPagination:

    def setup(self):
        self.app = setup_noDB()


    def test_basic_pagination(self):
        page = self.app.get('/paginated')
        assert ('<div id="pager"><span class="pager_curpage">1</span>'
            ' <a class="pager_link" href="/paginated?page=2">2</a>'
            ' <a class="pager_link" href="/paginated?page=3">3</a>'
            ' <span class="pager_dotdot">..</span>'
            ' <a class="pager_link" href="/paginated?page=5">5</a></div>'
            in page)
        assert '<ul id="data"><li>0</li><li>1</li>' in page, page
        assert '<li>8</li><li>9</li></ul>' in page, page
        page = self.app.get('/paginated?page=2')
        assert '<li>0</li>' not in page, page
        assert '<li>10</li>' in page, page

    def test_pagination_with_validation(self):
        page = self.app.get('/paginated_validated/1')
        assert ('<title>Pagination Test</title>'
            in page), page
        assert '<ul id="data"><li>0</li><li>1</li>' in page, page
        assert '<li>8</li><li>9</li></ul>' in page, page
        page = self.app.get('/paginated_validated/1?page=2')
        assert '<li>0</li>' not in page, page
        assert '<li>10</li>' in page, page
