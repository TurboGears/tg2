from tests.test_stack import TestConfig, app_from_config


def setup_noDB():
    base_config = TestConfig(folder='rendering',
            values={
                'use_sqlalchemy': False
            })
    return app_from_config(base_config)


_pager = ('<div id="pager"><span class="pager_curpage">1</span>'
    ' <a class="pager_link" href="%(url)s?page=2">2</a>'
    ' <a class="pager_link" href="%(url)s?page=3">3</a>'
    ' <span class="pager_dotdot">..</span>'
    ' <a class="pager_link" href="%(url)s?page=5">5</a></div>')

_data = '<ul id="data">%s</ul>' % ''.join(
        '<li>%d</li>' % i for i in range(10))


class TestPagination:

    def setup(self):
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
        page = self.app.get(url)

        assert '/multiple_paginators/42?testdata2_page=2' in page
        assert '/multiple_paginators/42?testdata_page=2' in page

        url = '/multiple_paginators/42?testdata_page=2'
        page = self.app.get(url)

        assert '/multiple_paginators/42?testdata2_page=2&testdata_page=2' in page
        assert '/multiple_paginators/42?testdata_page=4' in page

        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page
        assert '<li>142</li>' in page
        assert '<li>151</li>' in page

        url = '/multiple_paginators/42?testdata2_page=2'
        page = self.app.get(url)

        assert '/multiple_paginators/42?testdata2_page=2&testdata_page=2' in page, str(page)
        assert '/multiple_paginators/42?testdata2_page=4' in page

        assert '<li>0</li>' in page
        assert '<li>9</li>' in page
        assert '<li>151</li>' not in page
        assert '<li>161</li>' in page