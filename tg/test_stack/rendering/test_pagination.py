from tg.test_stack import TestConfig, app_from_config


def setup_noDB():
    base_config = TestConfig(folder='rendering',
            values={
                'use_sqlalchemy': False
            })
    return app_from_config(base_config)


def test_basic_pagination():
    app = setup_noDB()
    page = app.get('/paginated')
    print page
    assert ('<div id="pager"><span class="pager_curpage">1</span>'
        ' <a class="pager_link" href="/paginated?page=2">2</a>'
        ' <a class="pager_link" href="/paginated?page=3">3</a>'
        ' <span class="pager_dotdot">..</span>'
        ' <a class="pager_link" href="/paginated?page=5">5</a></div>'
        in page)
    assert '<ul id="data"><li>0</li><li>1</li>' in page
    assert '<li>8</li><li>9</li></ul>' in page
