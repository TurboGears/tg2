# -*- coding: utf-8 -*-
import datetime
import json
import re
from functools import partial
from json import loads

import pytest
from crank.util import get_params_with_argspec
from webtest import TestApp

import tests
import tg
from tests.base import (
    TestWSGIController,
    data_dir,
    make_app,
    setup_session_dir,
    teardown_session_dir,
)
from tg.configuration.utils import TGConfigError
from tg.configurator.fullstack import FullStackApplicationConfigurator
from tg.controllers import DecoratedController, TGController, abort
from tg.controllers.util import validation_errors_response
from tg.decorators import Decoration, before_call, before_render, expose, validate
from tg.i18n import lazy_ugettext as l_
from tg.support.converters import asbool, asint
from tg.validation import Convert, RequireValue, TGValidationError


def setup_module():
    setup_session_dir()

def teardown_module():
    teardown_session_dir()


class controller_based_validate(validate):
    def __init__(self, error_handler=None, *args, **kw):
        self.error_handler = error_handler
        self.needs_controller = True

        class Validators(object):
            def validate(self, controller, params):
                return params

        self.validators = Validators()

BoolValidator = Convert(asbool)
IntValidator = Convert(asint, msg="Please enter an integer value")

class EmailValidator:
    RE = re.compile(r"\w+@\w+\.\w+")

    @staticmethod
    def to_python(value):
        if not EmailValidator.RE.match(value):
            raise TGValidationError("Not an email address")
        return value

class ColonLessGenericValidator(object):
    def validate(self, value):
        raise TGValidationError('Unknown Error', value, {'_the_form':'Unknown Error'})

class ThrowAwayValidationIntentValidator(object):
    def validate(self, value):
        tg.request.validation.intent = None
        raise TGValidationError('Unknown Error', value, {'_the_form':'Unknown Error'})

def error_handler_function(controller_instance, uid, num):
    return 'UID: %s' % uid


def ControllerWrapperForErrorHandler(caller):
    def call(*args, **kw):
        value = caller(*args, **kw)
        return value + 'X'
    return call


class ErrorHandlerCallable(object):
    def __call__(self, controller_instance, uid, num):
        return 'UID: %s' % uid

class BasicTGController(TGController):
    @expose()
    @validate(ColonLessGenericValidator())
    def validator_without_columns(self, **kw):
        return tg.request.validation.errors['_the_form']

    @expose('json:')
    @validate(validators={"some_int": IntValidator})
    def validated_int(self, some_int):
        assert isinstance(some_int, int)
        return dict(response=some_int)

    @expose('json:')
    @validate(validators={"a": IntValidator})
    def validated_and_unvalidated(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, str)
        return dict(int=a, str=b)

    @expose()
    @controller_based_validate()
    def validate_controller_based_validator(self, *args, **kw):
        return 'ok'

    @expose('json:')
    @validate(validators={"a": IntValidator, "someemail": EmailValidator})
    def two_validators(self, a=None, someemail=None, *args):
        errors = tg.request.validation.errors
        values = tg.request.validation.values
        return dict(a=a, someemail=someemail,
                    errors=str(errors), values=str(values))

    @expose('json:')
    @validate(validators={"a": IntValidator})
    def with_default_shadow(self, a, b=None ):
        """A default value should not cause the validated value to disappear"""
        assert isinstance( a, int ), type(a)
        return {
            'int': a,
        }

    @expose('json:')
    @validate(validators={
        "a": IntValidator,"b":IntValidator,"c":IntValidator,"d":IntValidator
    })
    def with_default_shadow_long(self, a, b=None,c=None,d=None ):
        """A default value should not cause the validated value to disappear"""
        assert isinstance( a, int ), type(a)
        assert isinstance( b, int ), type(b)
        assert isinstance( c, int ), type(c)
        assert isinstance( d, int ), type(d)
        return {
            'int': [a,b,c,d],
        }

    @expose()
    def set_lang(self, lang=None):
        tg.session['tg_lang'] = lang
        tg.session.save()
        return 'ok'

    @expose('json:')
    @before_render(lambda rem,params,output:output.update({'GOT_ERROR':'HOOKED'}))
    def hooked_error_handler(self, *args, **kw):
        return dict(GOT_ERROR='MISSED HOOK')

    @expose()
    @validate({'v':IntValidator}, error_handler=hooked_error_handler)
    def with_hooked_error_handler(self, *args, **kw):
        return dict(GOT_ERROR='NO ERROR')

    @expose()
    def error_handler(self, *args, **kw):
        return 'ERROR HANDLER!'

    @expose('json:')
    @validate(validators={"some_int": IntValidator},
              error_handler=error_handler)
    def validate_other_error_handler(self, some_int):
        return dict(response=some_int)

    def unexposed_error_handler(self, uid, **kw):
        return 'UID: %s' % uid

    @expose()
    @validate({'uid': IntValidator,
               'num': IntValidator},
              error_handler=unexposed_error_handler)
    def validate_unexposed(self, uid, num):
        return 'HUH'

    @expose()
    @validate({'num': IntValidator},
              error_handler=partial(unexposed_error_handler,
                                    uid=5))
    def validate_partial(self, num):
        return 'HUH'

    @expose()
    @validate({'uid': IntValidator,
               'num': IntValidator},
              error_handler=error_handler_function)
    def validate_function(self, uid, num):
        return 'HUH'

    @expose()
    @validate({'uid': IntValidator,
               'num': IntValidator},
              error_handler=ErrorHandlerCallable())
    def validate_callable(self, uid, num):
        return 'HUH'

    @expose()
    @validate({'uid': IntValidator},
              error_handler=ErrorHandlerCallable())
    @validate({'num': IntValidator},
              error_handler=abort(412, error_handler=True))
    def validate_multi(self, uid, num):
        return str(uid+num)

    @expose()
    @validate({'uid': IntValidator},
              error_handler=abort(412, error_handler=True))
    def abort_error_handler(self):
        return 'HUH'

    @expose()
    @validate({'uid': IntValidator},
              error_handler=validation_errors_response)
    def validate_json_errors(self):
        return 'HUH'

    @expose()
    def validate_json_errors_complex_types(self, date):
        tg.request.validation.values = {'date': datetime.datetime.utcnow()}
        return validation_errors_response()

    @expose()
    @before_call(lambda remainder, params: params.setdefault('num', 5))
    def hooked_error_handler(self, uid, num):
        return 'UID: %s, NUM: %s' % (uid, num)

    @expose()
    @validate(ThrowAwayValidationIntentValidator(),
              error_handler=abort(412, error_handler=True))
    def throw_away_intent(self, uid):
        if tg.request.validation.exception:
            return 'ERROR'
        return 'UHU?'

    @expose()
    @validate(error_handler=hooked_error_handler)
    def passthrough_validation(self, uid):
        return str(uid)

    @expose()
    @validate({'uid': IntValidator},
              error_handler=hooked_error_handler)
    def validate_hooked(self, uid):
        return 'HUH'

    # Decorate validate_hooked with a controller wrapper
    Decoration.get_decoration(hooked_error_handler)\
        ._register_controller_wrapper(ControllerWrapperForErrorHandler)

    @expose()
    def manually_handle_validation(self):
        # This is done to check that we don't break compatibility
        # with external modules that perform custom validation like tgext.socketio

        controller = self.__class__.validate_function
        args = (2, 'NaN')
        context = tg.request.environ["tg.locals"]
        try:
            output = ''
            validate_params = get_params_with_argspec(controller, {}, args)
            params = DecoratedController._perform_validate(controller,
                                                           validate_params,
                                                           context)
        except TGValidationError as inv:
            obj, error_handler,_ = DecoratedController._process_validation_errors(
                controller, args, {}, inv, context
            )
            output = error_handler(obj, *args)
        return output

    @expose(content_type='text/plain')
    @validate({
        'num': Convert(int, l_('This must be a number'))
    }, error_handler=validation_errors_response)
    def post_pow2(self, num=-1):
        return str(num*num)

    @expose(content_type='text/plain')
    @validate({
        'num': Convert(int, l_('This must be a number'), default=0)
    }, error_handler=validation_errors_response)
    def post_pow2_opt(self, num=-1):
        return str(num*num)

    @expose(content_type='text/plain')
    @validate({
        'num': Convert(int, str('àèìòù'))
    }, error_handler=validation_errors_response)
    def unicode_error_pow(self, num=-1):
        return str(num*num)

    @expose(content_type='text/plain')
    @validate({
        'num': Convert(int, l_(str('àèìòù')))
    }, error_handler=validation_errors_response)
    def lazy_unicode_error_pow(self, num=-1):
        return str(num * num)

    @expose(content_type='text/plain')
    @validate({
        'val': Convert(lambda v: int(v) > 0 or int('ERROR'))
    }, error_handler=validation_errors_response)
    def chain_validation_0(self, val):
        return '>0'

    @expose(content_type='text/plain')
    @validate({
        'val': Convert(lambda v: int(v) > 1 or int('ERROR'))
    }, error_handler=chain_validation_0, chain_validation=True)
    def chain_validation_1(self, val):
        return '>1'

    @expose(content_type='text/plain')
    @validate({
        'val': Convert(lambda v: int(v) > 2 or int('ERROR'))
    }, error_handler=chain_validation_1, chain_validation=True)
    def chain_validation_2(self, val):
        return '>2'

    @expose(content_type='text/plain')
    @validate({
        'val': Convert(lambda v: int(v) > 3 or int('ERROR'))
    }, error_handler=chain_validation_2, chain_validation=True)
    def chain_validation_begin(self, val):
        return '>3'

    @expose(content_type='text/plain')
    @validate({
        'val': RequireValue(msg=l_("Value is required"))
    }, error_handler=validation_errors_response)
    def require_value(self, val=None):
        return val


class TestTGController(TestWSGIController):
    def setup_method(self):
        tg.config.update({
            'paths': {'root': data_dir},
            'package': tests,
        })

        self.app = make_app(BasicTGController, config_options={
            'i18n.enabled': True,
            'trace_errors.enable': False,
            'errorpage.enabled': False
        })
        TestWSGIController.setup_method(self)

    def test_basic_validation_and_jsonification(self):
        """Ensure you can pass in a dictionary of validators"""
        form_values = {"some_int": 22}
        resp = self.app.post('/validated_int', form_values)
        assert '{"response": 22}'in resp, resp

    def test_validation_other_error_handler(self):
        form_values = {"some_int": 'TEXT'}
        resp = self.app.post('/validate_other_error_handler', form_values)
        assert 'ERROR HANDLER!'in resp, resp

    def test_validator_without_columns(self):
        form_values = {"some_int": 22}
        resp = self.app.post('/validator_without_columns', form_values)
        assert 'Unknown Error' in resp, resp

    def test_for_other_params_after_validation(self):
        """Ensure that both validated and unvalidated data make it through"""
        form_values = {'a': 1, 'b': "string"}
        resp = self.app.post('/validated_and_unvalidated', form_values)
        assert '"int": 1' in resp
        assert '"str": "string"' in resp, resp

    def test_validation_shadowed_by_defaults( self ):
        """Catch regression on positional argument validation with defaults"""
        resp = self.app.post('/with_default_shadow/1?b=string')
        assert '"int": 1' in resp, resp

    def test_optional_shadowed_by_defaults( self ):
        """Catch regression on optional arguments being reverted to un-validated"""
        resp = self.app.post('/with_default_shadow_long/1?b=2&c=3&d=4')
        assert '"int": [1, 2, 3, 4]' in resp, resp

    def test_validation_fails_with_no_error_handler(self):
        form_values = {'a':'asdf', 'b':"string"}

        with pytest.raises(AssertionError):
            resp = self.app.post('/validated_and_unvalidated', form_values)

    def test_two_validators_errors(self):
        """Ensure that multiple validators are applied correctly"""
        form_values = {'a': '1', 'someemail': "guido@google.com"}
        resp = self.app.post('/two_validators', form_values)
        content = loads(resp.body.decode('utf-8'))
        assert content['a'] == 1

    def test_validation_errors(self):
        """Ensure that dict validation produces a full set of errors"""
        form_values = {'a': '1', 'someemail': "guido~google.com"}
        resp = self.app.post('/two_validators', form_values)
        content = loads(resp.body.decode('utf-8'))
        errors = content.get('errors', None)
        assert errors, 'There should have been at least one error'
        assert 'someemail' in errors, \
            'The email was invalid and should have been reported in the errors'

    def test_controller_based_validator(self):
        """Test controller based validation"""
        resp = self.app.post('/validate_controller_based_validator')
        assert 'ok' in resp, resp

    def test_hook_after_validation_error(self):
        resp = self.app.post('/with_hooked_error_handler?v=a')
        assert 'HOOKED' in resp, resp

    def test_validation_error_has_message(self):
        e = TGValidationError('This is a validation error')
        assert str(e) == 'This is a validation error'

    def test_validate_partial(self):
        resp = self.app.post('/validate_partial', {'num': 'NaN'})
        assert resp.text == 'UID: 5', resp

    def test_validate_unexposed(self):
        resp = self.app.post('/validate_unexposed', {'uid': 2,
                                                     'num': 'NaN'})
        assert resp.text == 'UID: 2', resp

    def test_validate_function(self):
        resp = self.app.post('/validate_function', {'uid': 2,
                                                    'num': 'NaN'})
        assert resp.text == 'UID: 2', resp

    def test_validate_callable(self):
        resp = self.app.post('/validate_callable', {'uid': 2,
                                                    'num': 'NaN'})
        assert resp.text == 'UID: 2', resp

    def test_validate_multi(self):
        resp = self.app.post('/validate_multi', {'uid': 'NaN', 'num': 2})
        assert resp.text == 'UID: NaN', resp

        resp = self.app.post('/validate_multi', {'uid': 2, 'num': 'NaN'}, status=412)
        assert resp.status.startswith('412')

        resp = self.app.post('/validate_multi', {'uid': 2, 'num': 2})
        assert resp.text == '4', resp

        resp = self.app.post('/validate_multi', {'uid': 'NaN', 'num': 'NaN'})
        assert resp.text == 'UID: NaN', resp

    def test_validate_hooked(self):
        resp = self.app.post('/validate_hooked', {'uid': 'NaN'})
        assert resp.text == 'UID: NaN, NUM: 5X', resp

    def test_manually_handle_validation(self):
        # This is done to check that we don't break compatibility
        # with external modules that perform custom validation like tgext.socketio
        resp = self.app.post('/manually_handle_validation')
        assert resp.text == 'UID: 2', resp

    def test_abort_error_handler(self):
        resp = self.app.post('/abort_error_handler', {'uid': 'NaN'}, status=412)
        assert resp.status.startswith('412')

    def test_json_error_handler(self):
        resp = self.app.post('/validate_json_errors', {'uid': 'NaN'}, status=412)
        assert resp.json['errors']['uid'] == 'Please enter an integer value'

    def test_json_error_handler_complex_type(self):
        resp = self.app.post('/validate_json_errors_complex_types', {'date': '2014-01-01'},
                             status=412)
        assert resp.json['values']['date'] == '2014-01-01', resp

    def test_throw_way_validation_intent(self):
        # This should actually never happen.
        # It requires the validator to mess up with TG internals, it's just to provide full coverage.
        resp = self.app.post('/throw_away_intent', {'uid': 5})
        assert resp.text == 'ERROR', resp

    def test_passthrough_validation(self):
        # This should actually never happen.
        # It requires the validator to mess up with TG internals, it's just to provide full coverage.
        resp = self.app.post('/passthrough_validation', {'uid': 5})
        assert resp.text == '5', resp

    def test_convert_validation(self):
        resp = self.app.post('/post_pow2', {'num': '5'})
        assert resp.text == '25', resp

    def test_convert_validation_fail(self):
        resp = self.app.post('/post_pow2', {'num': 'HELLO'}, status=412)
        assert 'This must be a number' in resp.json['errors']['num']

    def test_convert_validation_missing(self):
        resp = self.app.post('/post_pow2', {'num': ''}, status=412)
        assert 'This must be a number' in resp.json['errors']['num']

        resp = self.app.post('/post_pow2', status=412)
        assert 'This must be a number' in resp.json['errors']['num']

    def test_convert_validation_optional(self):
        resp = self.app.post('/post_pow2_opt', {'num': 'HELLO'}, status=412)
        assert 'This must be a number' in resp.json['errors']['num']

        resp = self.app.post('/post_pow2_opt', {'num': '5'})
        assert resp.text == '25', resp

        resp = self.app.post('/post_pow2_opt', {'num': ''})
        assert resp.text == '0', resp

        resp = self.app.post('/post_pow2_opt')
        assert resp.text == '0', resp

    def test_validation_errors_unicode(self):
        resp = self.app.post('/unicode_error_pow', {'num': 'NOT_A_NUMBER'}, status=412)
        assert resp.json['errors']['num'] == str('àèìòù'), resp.json

    def test_validation_errors_lazy_unicode(self):
        resp = self.app.post('/lazy_unicode_error_pow', {'num': 'NOT_A_NUMBER'}, status=412)
        assert resp.json['errors']['num'] == str('àèìòù'), resp.json

    def test_requirevalue_validation(self):
        resp = self.app.post('/require_value', {"val": "hello"})
        assert resp.text == 'hello', resp

        resp = self.app.post('/require_value', {}, status=412)
        assert resp.json["errors"]["val"] == 'Value is required', resp


class TestChainValidation(TestWSGIController):
    def setup_method(self):
        tg.config.update({
            'paths': {'root': data_dir},
            'package': tests,
        })

        self.app = make_app(BasicTGController, config_options={
            'i18n.enabled': True
        })

        TestWSGIController.setup_method(self)

    def test_no_chain_validation(self):
        res = self.app.get('/chain_validation_begin', params={'val': 4})
        assert res.text == '>3'

        res = self.app.get('/chain_validation_begin', params={'val': 3})
        assert res.text == '>2'

    def test_single_chain_validation(self):
        res = self.app.get('/chain_validation_begin', params={'val': 2})
        assert res.text == '>1'

    def test_double_chain_validation(self):
        res = self.app.get('/chain_validation_begin', params={'val': 1})
        assert res.text == '>0'

    def test_last_chain_validation(self):
        res = self.app.get('/chain_validation_begin', params={'val': 0}, status=412)
        assert res.json == json.loads('{"errors":{"val":"Invalid"},"values":{"val":"0"}}')


class TestValidationConfiguration:
    def create_app(self, root_controller, options=None):
        cfg = FullStackApplicationConfigurator()
        cfg.update_blueprint({'root_controller': root_controller})
        cfg.update_blueprint(options or {})

        app = TestApp(cfg.make_wsgi_app({
            'debug': False,
            'errorpage.enabled': False,
            'trace_errors.enable': False
        }, {}))
        return app

    def test_no_validation_function(self):
        class FakeSchema:
            pass

        class RootController(TGController):
            @validate(FakeSchema())
            @expose("text/plain")
            def test(self, **kwargs):
                return "HI"

        app = self.create_app(RootController())

        with pytest.raises(TGConfigError) as exc_info:
            app.get("/test", {"value": 5})
        assert "No validation validator function found for" in str(exc_info.value)
        assert "FakeSchema" in str(exc_info.value)

    def test_custom_validation(self):
        class FakeSchema:
            pass

        def validate_fake_schema(schema, params):
            if params.get("fail"):
                raise TGValidationError("Invalid params", value=params,
                                        error_dict={"fail": "Fail is true"})
            return params

        class RootController(TGController):
            @validate(FakeSchema())
            @expose("text/plain")
            def test(self, **kwargs):
                if tg.request.validation.errors:
                    return str(tg.request.validation.errors)
                return "HI"

        app = self.create_app(RootController(), {
            "validation.validators": {FakeSchema: validate_fake_schema}
        })

        resp = app.get("/test", {"value": 5})
        assert resp.text == "HI"

        resp = app.get("/test", {"fail": 1})
        assert "Fail is true" in resp.text

    def test_custom_validation_error(self):
        class FakeSchema:
            pass

        def validate_fake_schema(schema, params):
            if params.get("fail"):
                raise FakeError()
            return params

        class FakeError(Exception):
            pass

        def explode_fake_error(error):
            return {"values": {"fail": True}, "errors": "fail was true"}

        class RootController(TGController):
            @validate(FakeSchema())
            @expose("text/plain")
            def test(self, **kwargs):
                if tg.request.validation.errors:
                    return str(tg.request.validation.errors)
                return "HI"

        app = self.create_app(RootController(), {
            "validation.validators": {FakeSchema: validate_fake_schema},
            "validation.exceptions": [FakeError],
            "validation.explode": {FakeError: explode_fake_error}
        })

        resp = app.get("/test", {"value": 5})
        assert resp.text == "HI"

        resp = app.get("/test", {"fail": 1})
        assert "fail was true" in resp.text

        # Do not provide explode function
        app = self.create_app(RootController(), {
            "validation.validators": {FakeSchema: validate_fake_schema},
            "validation.exceptions": [FakeError]
        })
        with pytest.raises(TGConfigError) as exc_info:
            resp = app.get("/test", {"fail": 1})
        assert "No validation explode function found for" in str(exc_info.value)
        assert "FakeError" in str(exc_info.value)

        # Do not provide missing explode function
        app = self.create_app(RootController(), {
            "validation.validators": {FakeSchema: validate_fake_schema},
            "validation.exceptions": [FakeError],
            "validation.explode": {FakeError: None}
        })
        with pytest.raises(TGConfigError) as exc_info:
            resp = app.get("/test", {"fail": 1})
        assert "No validation explode function found for" in str(exc_info.value)
        assert "FakeError" in str(exc_info.value)
