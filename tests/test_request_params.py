# -*- coding: utf-8 -*-
import json

import pytest
from webtest import TestApp

import tg
from tg import MinimalApplicationConfigurator, TGController, expose
from tg.configuration import config
from tg.controllers import RestController
from tg.decorators import before_call, before_validate, decode_params, paginate, validate
from tg.support.converters import asint
from tg.validation import Convert

IntValidator = Convert(asint, msg="Please enter an integer value")


def _copy_x_to_copied_x(remainder, params):
    params.setdefault('copied_x', params['x'])


class TestRequestParameterEquivalence(object):
    @pytest.mark.parametrize('source', ['query', 'positional', 'multipart', 'json'])
    def test_required_action_argument_is_satisfied_by_equivalent_parameter_sources(
        self, app, source
    ):
        resp = _request_with_x(app, '/echo', source)

        assert resp.json_body == {'x': '5'}

    @pytest.mark.parametrize('source', ['query', 'positional', 'multipart', 'json'])
    def test_validation_sees_equivalent_parameter_sources(self, app, source):
        resp = _request_with_x(app, '/validated', source)

        assert resp.json_body == {'x': 5, 'type': 'int'}

    def test_validation_accepts_json_native_types(self, app):
        resp = app.post_json('/validated', {'x': 5})

        assert resp.json_body == {'x': 5, 'type': 'int'}

    def test_json_content_type_media_type_is_case_insensitive(self, app):
        resp = app.post(
            '/echo',
            params=json.dumps({'x': '5'}),
            content_type='Application/JSON',
        )

        assert resp.json_body == {'x': '5'}

    @pytest.mark.parametrize('source', ['query', 'multipart', 'json'])
    def test_before_validate_hook_sees_equivalent_parameter_sources(self, app, source):
        resp = _request_with_x(app, '/before_validate_hooked', source)

        assert resp.json_body == {'x': '5', 'copied_x': '5'}

    @pytest.mark.parametrize('source', ['query', 'multipart', 'json'])
    def test_before_call_hook_sees_equivalent_parameter_sources(self, app, source):
        resp = _request_with_x(app, '/before_call_hooked', source)

        assert resp.json_body == {'x': '5', 'copied_x': '5'}

    @pytest.mark.parametrize('source', ['query', 'positional', 'multipart', 'json'])
    def test_controller_before_hook_sees_equivalent_parameter_sources(
        self, app, source
    ):
        resp = _request_with_x(app, '/controller_before_hooked', source)

        assert resp.json_body == {'x': '5'}

    @pytest.mark.parametrize('source', ['query', 'multipart', 'json'])
    def test_paginate_sees_equivalent_parameter_sources(self, app, source):
        resp = _request_with_page(app, source)

        assert resp.json_body == {'page': 3}

    @pytest.mark.parametrize('source', ['query', 'multipart', 'json'])
    def test_rest_method_override_uses_equivalent_parameter_sources(
        self, rest_app, source
    ):
        resp = _request_with_method_override(rest_app, source)

        assert resp.json_body == {'action': 'put', 'x': '5'}

    def test_multipart_body_combines_with_query_params_on_collision(self, app):
        resp = app.post(
            '/echo?x=query',
            params={'x': 'multipart'},
            upload_files=[_empty_file()],
        )

        assert resp.json_body == {'x': ['query', 'multipart']}

    def test_json_body_overrides_query_params_on_collision(self, app):
        resp = app.post_json('/echo?x=query', {'x': 'json'})

        assert resp.json_body == {'x': 'json'}

    def test_decode_params_decorator_can_coexist_with_json_params(self, app):
        resp = app.post_json('/decode_decorated?x=query', {'x': 'json'})

        assert resp.json_body == {'x': 'json'}

    def test_empty_json_body_is_bad_request(self, app):
        app.post('/optional', params='', content_type='application/json', status=400)

    def test_invalid_json_body_is_bad_request(self, app):
        app.post('/optional', params='{', content_type='application/json', status=400)

    @pytest.mark.parametrize('json_body', [
        ['not', 'an', 'object'],
        [['x', '5']],
    ])
    def test_non_object_json_body_is_bad_request(self, app, json_body):
        app.post(
            '/optional',
            params=json.dumps(json_body),
            content_type='application/json',
            status=400,
        )

    def test_json_params_are_disabled_by_default(self, default_config_app):
        resp = default_config_app.post_json('/optional', {'x': '5'})

        assert resp.json_body == {'x': 'default'}

    def test_json_params_can_be_explicitly_disabled(self, json_disabled_app):
        resp = json_disabled_app.post_json('/optional', {'x': '5'})

        assert resp.json_body == {'x': 'default'}

    def test_json_params_respect_ignore_parameters(self, ignored_params_app):
        resp = ignored_params_app.post_json('/filtered_args_params', {
            'ignored': 'removed',
            'kept': 'kept',
        })

        assert resp.json_body == {
            'x': None,
            'y': None,
            'ignored': None,
            'kept': 'kept',
        }

    def test_json_params_are_available_in_routing_args(self, routing_args_app):
        resp = routing_args_app.post_json('/routing_args', {'x': '5'})

        assert resp.json_body == {'x': '5'}


class TestRequestParameterEquivalenceWithUrlArgs(object):
    @pytest.mark.parametrize('source', ['query', 'multipart', 'json'])
    def test_url_positional_args_win_when_mixed_with_parameter_sources(
        self, app, source
    ):
        resp = _request_with_positional_x_and_y(app, source)

        assert resp.json_body == {'x': '5', 'y': '6'}

    def test_request_args_params_uses_url_arg_over_json_param(self, app):
        resp = app.post_json('/filtered_args_params/5', {'x': 'json', 'y': '6'})

        assert resp.json_body == {
            'x': '5',
            'y': '6',
            'ignored': None,
            'kept': None,
        }


class ParameterRestController(RestController):
    @expose('json:')
    def post(self, x=None, **kw):
        return dict(action='post', x=x)

    @expose('json:')
    def put(self, x=None, **kw):
        return dict(action='put', x=x)


class RequestParameterController(TGController):
    def _before(self, *args, **kw):
        self._before_params = kw.copy()
        if args:
            self._before_params['x'] = args[0]

    @expose()
    def index(self):
        return 'request params tests'

    @expose('json:')
    def echo(self, x):
        return dict(x=x)

    @expose('json:')
    @validate(validators=dict(x=IntValidator))
    def validated(self, x):
        return dict(x=x, type=type(x).__name__)

    @expose('json:')
    @decode_params()
    def decode_decorated(self, x=None):
        return dict(x=x)

    @expose('json:')
    @before_validate(_copy_x_to_copied_x)
    def before_validate_hooked(self, x, copied_x=None):
        return dict(x=x, copied_x=copied_x)

    @expose('json:')
    @before_call(_copy_x_to_copied_x)
    def before_call_hooked(self, **kw):
        return dict(x=kw.get('x'), copied_x=kw.get('copied_x'))

    @expose('json:')
    def controller_before_hooked(self, x=None):
        return dict(x=self._before_params.get('x'))

    @expose('json:')
    @paginate('items')
    def paginated(self, **kw):
        return dict(page=tg.request.paginators['items'].paginate_page)

    @expose('json:')
    def mixed(self, x, y):
        return dict(x=x, y=y)

    @expose('json:')
    def filtered_args_params(self, x=None, y=None, **kw):
        params = tg.request.args_params
        return dict(
            x=params.get('x'),
            y=params.get('y'),
            ignored=params.get('ignored'),
            kept=params.get('kept'),
        )

    @expose('json:')
    def routing_args(self, **kw):
        return dict(x=tg.request.dispatch_state.routing_args.get('x'))

    @expose('json:')
    def optional(self, x='default'):
        return dict(x=x)


class RestParameterRootController(TGController):
    @expose()
    def index(self):
        return 'request params rest tests'

    rest = ParameterRestController()


@pytest.fixture
def app():
    yield _make_app(RequestParameterController())
    _reset_global_config()


@pytest.fixture
def rest_app():
    yield _make_app(RestParameterRootController())
    _reset_global_config()


@pytest.fixture
def default_config_app():
    _reset_global_config()
    cfg = MinimalApplicationConfigurator()
    cfg.update_blueprint({'root_controller': RequestParameterController()})
    yield TestApp(cfg.make_wsgi_app({}, {}))
    _reset_global_config()


@pytest.fixture
def json_disabled_app():
    yield _make_app(RequestParameterController(), decode_json_params=False)
    _reset_global_config()


@pytest.fixture
def ignored_params_app():
    yield _make_app(RequestParameterController(), ignore_parameters=['ignored'])
    _reset_global_config()


@pytest.fixture
def routing_args_app():
    yield _make_app(RequestParameterController(), enable_routing_args=True)
    _reset_global_config()


def _request_with_x(app, path, source):
    if source == 'query':
        return app.get('%s?x=5' % path)
    if source == 'positional':
        return app.get('%s/5' % path)
    if source == 'multipart':
        return app.post(path, params={'x': '5'}, upload_files=[_empty_file()])
    if source == 'json':
        return app.post_json(path, {'x': '5'})
    raise AssertionError('unknown parameter source %s' % source)


def _request_with_page(app, source):
    if source == 'query':
        return app.get('/paginated?page=3')
    if source == 'multipart':
        return app.post('/paginated', params={'page': '3'}, upload_files=[_empty_file()])
    if source == 'json':
        return app.post_json('/paginated', {'page': '3'})
    raise AssertionError('unknown parameter source %s' % source)


def _request_with_method_override(app, source):
    if source == 'query':
        return app.post('/rest?_method=PUT&x=5')
    if source == 'multipart':
        return app.post(
            '/rest',
            params={'_method': 'PUT', 'x': '5'},
            upload_files=[_empty_file()],
        )
    if source == 'json':
        return app.post_json('/rest', {'_method': 'PUT', 'x': '5'})
    raise AssertionError('unknown parameter source %s' % source)


def _request_with_positional_x_and_y(app, source):
    if source == 'query':
        return app.get('/mixed/5?x=from_params&y=6')
    if source == 'multipart':
        return app.post(
            '/mixed/5',
            params={'x': 'from_params', 'y': '6'},
            upload_files=[_empty_file()],
        )
    if source == 'json':
        return app.post_json('/mixed/5', {'x': 'from_params', 'y': '6'})
    raise AssertionError('unknown parameter source %s' % source)


def _empty_file():
    return ('attachment', 'empty.txt', b'')


def _make_app(root_controller, **config_options):
    _reset_global_config()
    cfg = MinimalApplicationConfigurator()
    app_config = {
        'root_controller': root_controller,
        'decode_json_params': True,
    }
    app_config.update(config_options)
    cfg.update_blueprint(app_config)
    return TestApp(cfg.make_wsgi_app({}, {}))


def _reset_global_config():
    try:
        config.config_proxy.pop_process_config()
    except IndexError:
        pass
