from tg import config
from tg.test_stack import TestConfig, app_from_config
from routes import Mapper

def setup_noDB():
    class TestRoutesConfig(TestConfig):
        def setup_routes(self):
            config['routes.map'] = setup_map(self.paths['controllers'])

    base_config = TestRoutesConfig(folder='rendering', values={
        'use_sqlalchemy': False,
        'ignore_parameters': ["ignore", "ignore_me"]})
    return app_from_config(base_config)

def setup_map(controller_path):
    # These tests pass with the directory specified and without, but this
    # is the configuration recommended by the 2.0 docs so we'll go with that.
    map = Mapper(directory=controller_path, always_scan=True)

    map.connect('/regular/paginated/{page}',
        controller='routingtest',
        action='paginated',
        page=1)

    map.connect('/validated/paginated/{page}',
        controller='routingtest',
        action='paginated_validated',
        page=1)

    map.connect('/custom/{action}',
        controller='routingtest',
        action='index')

    map.connect('/{controller}/{action}',
        action='index')

    return map


class TestPagination:
    # Aside from the URLs, these tests are identical to
    # tg/test_stack/rendering/test_pagination.py

    def setup(self):
        self.app = setup_noDB()


    def test_basic_pagination(self):
        page = self.app.get('/regular/paginated/1')
        assert ('<div id="pager"><span class="pager_curpage">1</span>'
            ' <a class="pager_link" href="/regular/paginated/2">2</a>'
            ' <a class="pager_link" href="/regular/paginated/3">3</a>'
            ' <span class="pager_dotdot">..</span>'
            ' <a class="pager_link" href="/regular/paginated/5">5</a></div>'
            in page)
        assert '<ul id="data"><li>0</li><li>1</li>' in page, page
        assert '<li>8</li><li>9</li></ul>' in page, page
        page = self.app.get('/regular/paginated/2')
        assert '<li>0</li>' not in page, page
        assert '<li>10</li>' in page, page

    def test_pagination_with_validation(self):
        page = self.app.get('/validated/paginated')
        assert ('<title>Pagination Test</title>'
            in page), page
        assert '<ul id="data"><li>0</li><li>1</li>' in page, page
        assert '<li>8</li><li>9</li></ul>' in page, page
        page = self.app.get('/validated/paginated/2')
        assert '<li>0</li>' not in page, page
        assert '<li>10</li>' in page, page
