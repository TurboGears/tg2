# -*- coding: utf-8 -*-
from functools import partial
from nose.tools import raises
from nose import SkipTest
from crank.util import get_params_with_argspec

import tg
import tests
from json import loads
import datetime

from tg.controllers import TGController, DecoratedController, abort
from tg.controllers.util import validation_errors_response
from tg.decorators import expose, validate, before_render, before_call, Decoration
from tests.base import (TestWSGIController, data_dir,
    make_app, setup_session_dir, teardown_session_dir)

from tg._compat import PY3, unicode_text, u_, default_im_func
from tg.validation import TGValidationError, validation_errors, _ValidationStatus, Convert
from tg.i18n import lazy_ugettext as l_
from formencode import validators, Schema

import tw2.core as tw2c
import tw2.forms as tw2f

class MovieForm(tw2f.TableForm):
    title = tw2f.TextField(validator=tw2c.Required)
    year = tw2f.TextField(size=4, validator=tw2c.IntValidator)
movie_form = MovieForm(action='save_movie')

class Pwd(Schema):
    pwd1 = validators.String(not_empty=True)
    pwd2 = validators.String(not_empty=True)
    chained_validators = [validators.FieldsMatch('pwd1', 'pwd2')]

class FormWithFieldSet(tw2f.TableForm):
    class fields1(tw2f.ListFieldSet):
        f1 = tw2f.TextField(validator=tw2c.Required)

    class fields2(tw2f.ListFieldSet):
        f2 = tw2f.TextField(validator=tw2c.IntValidator)

if not PY3:
    from tw.forms import TableForm, TextField
    from tw.api import WidgetsList

    class MyForm(TableForm):
        class fields(WidgetsList):
            """This WidgetsList is just a container."""
            title=TextField(validator = validators.NotEmpty())
            year = TextField(size=4, validator=validators.Int())
    myform = MyForm("my_form", action='create')
else:
    myform = None


def setup():
    setup_session_dir()

def teardown():
    teardown_session_dir()


class controller_based_validate(validate):
    def __init__(self, error_handler=None, *args, **kw):
        self.error_handler = error_handler
        self.needs_controller = True

        class Validators(object):
            def validate(self, controller, params, state):
                return params

        self.validators = Validators()

class ColonValidator(validators.FancyValidator):
    def validate_python(self, value, state):
        raise validators.Invalid('ERROR: Description', value, state)

class ColonLessGenericValidator(object):
    def validate(self, value, state=None):
        raise validators.Invalid('Unknown Error', value, {'_the_form':'Unknown Error'})

class ThrowAwayValidationIntentValidator(object):
    def validate(self, value, state=None):
        tg.request.validation.intent = None
        raise validators.Invalid('Unknown Error', value, {'_the_form':'Unknown Error'})

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
        return tg.request.validation['errors']['_the_form']

    @expose('json:')
    @validate(validators={"some_int": validators.Int()})
    def validated_int(self, some_int):
        assert isinstance(some_int, int)
        return dict(response=some_int)

    @expose('json:')
    @validate(validators={"a": validators.Int()})
    def validated_and_unvalidated(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode_text)
        return dict(int=a, str=b)

    @expose()
    @controller_based_validate()
    def validate_controller_based_validator(self, *args, **kw):
        return 'ok'

    @expose('json:')
    @validate(validators={"a": validators.Int(), "someemail": validators.Email()})
    def two_validators(self, a=None, someemail=None, *args):
        errors = tg.request.validation['errors']
        values = tg.request.validation['values']
        return dict(a=a, someemail=someemail,
                errors=str(errors), values=str(values))

    @expose('json:')
    @validate(validators={"a": validators.Int()})
    def with_default_shadow(self, a, b=None ):
        """A default value should not cause the validated value to disappear"""
        assert isinstance( a, int ), type(a)
        return {
            'int': a,
        }

    @expose('json:')
    @validate(validators={"e": ColonValidator()})
    def error_with_colon(self, e):
        errors = tg.request.validation['errors']
        return dict(errors=str(errors))

    @expose('json:')
    @validate(validators={
        "a": validators.Int(),"b":validators.Int(),"c":validators.Int(),"d":validators.Int()
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
    def display_form(self, **kwargs):
        return str(myform.render(values=kwargs))

    @expose('json:')
    @validate(form=myform)
    def process_form(self, **kwargs):
        kwargs['errors'] = tg.request.validation['errors']
        return dict(kwargs)

    @expose('json:')
    @validate(form=myform, error_handler=process_form)
    def send_to_error_handler(self, **kwargs):
        kwargs['errors'] = tg.request.validation['errors']
        return dict(kwargs)

    @expose('json')
    def tw2form_error_handler(self, **kwargs):
        return dict(errors=tg.request.validation['errors'])

    @expose('json:')
    @validate(form=movie_form, error_handler=tw2form_error_handler)
    def send_tw2_to_error_handler(self, **kwargs):
        return 'passed validation'

    @expose()
    @validate({'param': tw2c.IntValidator()},
              error_handler=validation_errors_response)
    def tw2_dict_validation(self, **kwargs):
        return 'NO_ERROR'

    @expose()
    @validate({'param': validators.Int()},
              error_handler=validation_errors_response)
    def formencode_dict_validation(self, **kwargs):
        return 'NO_ERROR'

    @expose('text/plain')
    @validate(form=FormWithFieldSet, error_handler=tw2form_error_handler)
    def tw2_fieldset_submit(self, **kwargs):
        return 'passed validation'

    @expose()
    def set_lang(self, lang=None):
        tg.session['tg_lang'] = lang
        tg.session.save()
        return 'ok'

    @expose()
    @validate(validators=Pwd())
    def password(self, pwd1, pwd2):
        if tg.request.validation['errors']:
            return "There was an error"
        else:
            return "Password ok!"

    @expose('json:')
    @before_render(lambda rem,params,output:output.update({'GOT_ERROR':'HOOKED'}))
    def hooked_error_handler(self, *args, **kw):
        return dict(GOT_ERROR='MISSED HOOK')

    @expose()
    @validate({'v':validators.Int()}, error_handler=hooked_error_handler)
    def with_hooked_error_handler(self, *args, **kw):
        return dict(GOT_ERROR='NO ERROR')

    @expose('json')
    @validate({'v': validators.Int()})
    def check_tmpl_context_compatibility(self, *args, **kw):
        return dict(tmpl_errors=str(tg.tmpl_context.form_errors),
                    errors=str(tg.request.validation['errors']))

    @expose()
    def error_handler(self, *args, **kw):
        return 'ERROR HANDLER!'

    @expose('json:')
    @validate(validators={"some_int": validators.Int()},
              error_handler=error_handler)
    def validate_other_error_handler(self, some_int):
        return dict(response=some_int)

    def unexposed_error_handler(self, uid, **kw):
        return 'UID: %s' % uid

    @expose()
    @validate({'uid': validators.Int(),
               'num': validators.Int()},
              error_handler=unexposed_error_handler)
    def validate_unexposed(self, uid, num):
        return 'HUH'

    @expose()
    @validate({'num': validators.Int()},
              error_handler=partial(unexposed_error_handler,
                                    uid=5))
    def validate_partial(self, num):
        return 'HUH'

    @expose()
    @validate({'uid': tw2c.IntValidator(),
               'num': tw2c.IntValidator()},
              error_handler=error_handler_function)
    def validate_function(self, uid, num):
        return 'HUH'

    @expose()
    @validate({'uid': validators.Int(),
               'num': validators.Int()},
              error_handler=ErrorHandlerCallable())
    def validate_callable(self, uid, num):
        return 'HUH'

    @expose()
    @validate({'uid': validators.Int()},
              error_handler=ErrorHandlerCallable())
    @validate({'num': validators.Int()},
              error_handler=abort(412, error_handler=True))
    def validate_multi(self, uid, num):
        return str(uid+num)

    @expose()
    @validate({'uid': validators.Int()},
              error_handler=abort(412, error_handler=True))
    def abort_error_handler(self):
        return 'HUH'

    @expose()
    @validate({'uid': validators.Int()},
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
    @validate({'uid': validators.Int()},
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
        try:
            output = ''
            validate_params = get_params_with_argspec(controller, {}, args)
            params = DecoratedController._perform_validate(controller,
                                                           validate_params)
        except validation_errors as inv:
            handler, output = DecoratedController._handle_validation_errors(controller,
                                                                            args, {},
                                                                            inv, None)

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


class TestTGController(TestWSGIController):
    def setUp(self):
        TestWSGIController.setUp(self)
        tg.config.update({
            'paths': {'root': data_dir},
            'package': tests,
        })

        self.app = make_app(BasicTGController, config_options={
            'i18n.enabled': True
        })

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

    @raises(AssertionError)
    def test_validation_fails_with_no_error_handler(self):
        form_values = {'a':'asdf', 'b':"string"}
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

    def test_form_validation(self):
        """Check @validate's handing of ToscaWidget forms instances"""
        if PY3: raise SkipTest()

        form_values = {'title': 'Razer', 'year': "2007"}
        resp = self.app.post('/process_form', form_values)
        values = loads(resp.body.decode('utf-8'))
        assert values['year'] == 2007

    def test_error_with_colon(self):
        resp = self.app.post('/error_with_colon', {'e':"fakeparam"})
        assert 'Description' in str(resp.body), resp.body

    def test_form_render(self):
        """Test that myform renders properly"""
        if PY3: raise SkipTest()

        resp = self.app.post('/display_form')
        assert 'id="my_form_title.label"' in resp, resp
        assert 'class="fieldlabel required"' in resp, resp
        assert "Title" in resp, resp

    def test_form_validation_error(self):
        """Test form validation with error message"""
        if PY3: raise SkipTest()

        form_values = {'title': 'Razer', 'year': "t007"}
        resp = self.app.post('/process_form', form_values)
        values = loads(resp.body.decode('utf-8'))
        assert "Please enter an integer value" in values['errors']['year'], \
            'Error message not found: %r' % values['errors']

    def test_form_validation_redirect(self):
        """Test form validation error message with redirect"""
        if PY3: raise SkipTest()

        form_values = {'title': 'Razer', 'year': "t007"}
        resp = self.app.post('/send_to_error_handler', form_values)
        values = loads(resp.body.decode('utf-8'))
        assert "Please enter an integer value" in values['errors']['year'], \
            'Error message not found: %r' % values['errors']

    def test_tw2form_validation(self):
        form_values = {'title': 'Razer', 'year': "t007"}
        resp = self.app.post('/send_tw2_to_error_handler', form_values)
        values = loads(resp.body.decode('utf-8'))
        assert "Must be an integer" in values['errors']['year'],\
        'Error message not found: %r' % values['errors']

    def test_tw2dict_validation(self):
        resp = self.app.post('/tw2_dict_validation', {'param': "7"})
        assert 'NO_ERROR' in str(resp.body)

        resp = self.app.post('/tw2_dict_validation', {'param': "hello"}, status=412)
        assert 'Must be an integer' in str(resp.body)

    def test_formencode_dict_validation(self):
        resp = self.app.post('/formencode_dict_validation', {'param': "7"})
        assert 'NO_ERROR' in str(resp.body), resp

        resp = self.app.post('/formencode_dict_validation', {'param': "hello"}, status=412)
        assert 'Please enter an integer value' in str(resp.body), resp

    def test_form_validation_translation(self):
        if PY3: raise SkipTest()

        """Test translation of form validation error messages"""
        form_values = {'title': 'Razer', 'year': "t007"}
        # check with language set in request header
        resp = self.app.post('/process_form', form_values,
            headers={'Accept-Language': 'de,ru,it'})
        values = loads(resp.body.decode('utf-8'))
        assert "Bitte eine ganze Zahl eingeben" in values['errors']['year'], \
            'No German error message: %r' % values['errors']
        resp = self.app.post('/process_form', form_values,
            headers={'Accept-Language': 'ru,de,it'})
        values = loads(resp.body.decode('utf-8'))
        assert u_("Введите числовое значение") in values['errors']['year'], \
            'No Russian error message: %r' % values['errors']
        # check with language set in session
        self.app.post('/set_lang/de')
        resp = self.app.post('/process_form', form_values,
            headers={'Accept-Language': 'ru,it'})
        values = loads(resp.body.decode('utf-8'))
        assert "Bitte eine ganze Zahl eingeben" in values['errors']['year'], \
            'No German error message: %r' % values['errors']

    def test_form_validation_error(self):
        """Test schema validation"""
        form_values = {'pwd1': 'me', 'pwd2': 'you'}
        resp = self.app.post('/password', form_values)
        assert "There was an error" in resp, resp
        form_values = {'pwd1': 'you', 'pwd2': 'you'}
        resp = self.app.post('/password', form_values)
        assert "Password ok!" in resp, resp

    def test_controller_based_validator(self):
        """Test controller based validation"""
        resp = self.app.post('/validate_controller_based_validator')
        assert 'ok' in resp, resp

    def test_hook_after_validation_error(self):
        resp = self.app.post('/with_hooked_error_handler?v=a')
        assert 'HOOKED' in resp, resp

    def test_check_tmpl_context_compatibility(self):
        resp = self.app.post('/check_tmpl_context_compatibility?v=a')
        resp = resp.json
        assert resp['errors'] == resp['tmpl_errors'], resp

    def test_validation_error_has_message(self):
        e = TGValidationError('This is a validation error')
        assert str(e) == 'This is a validation error'

    def test_tw2_fieldset(self):
        form_values = {'fields1:f1': 'Razer', 'fields2:f2': "t007"}
        resp = self.app.post('/tw2_fieldset_submit', form_values)
        values = loads(resp.body.decode('utf-8'))

        assert "Must be an integer" in values['errors'].get('fields2:f2', ''),\
        'Error message not found: %r' % values['errors']

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

    def test_ValidationStatus_asdict(self):
        vs = _ValidationStatus()
        assert vs['errors'] is vs.errors
        assert vs['values'] is vs.values
        assert vs['error_handler'] is vs.error_handler

        try:
            vs['this_does_not_exists']
        except KeyError:
            pass
        else:
            assert False, 'Should have raised KeyError'

    def test_backward_compatibility_decorator(self):
        deco = Decoration.get_decoration(BasicTGController.two_validators)

        validated_params = sorted(list(deco.validation.validators.keys()))
        assert validated_params == ["a", "someemail"], validated_params

        deco = Decoration.get_decoration(BasicTGController.tw2form_error_handler)
        assert deco.validation is None, deco.validation

    def test_convert_validation(self):
        resp = self.app.post('/post_pow2', {'num': '5'})
        assert resp.text == '25', resp

    def test_convert_validation_fail(self):
        resp = self.app.post('/post_pow2', {'num': 'HELLO'}, status=412)
        assert 'This must be a number' in resp.text, resp

    def test_convert_validation_missing(self):
        resp = self.app.post('/post_pow2', {'num': ''}, status=412)
        assert 'This must be a number' in resp.text, resp

        resp = self.app.post('/post_pow2', status=412)
        assert 'This must be a number' in resp.text, resp

    def test_convert_validation_optional(self):
        resp = self.app.post('/post_pow2_opt', {'num': 'HELLO'}, status=412)
        assert 'This must be a number' in resp.text, resp

        resp = self.app.post('/post_pow2_opt', {'num': '5'})
        assert resp.text == '25', resp

        resp = self.app.post('/post_pow2_opt', {'num': ''})
        assert resp.text == '0', resp

        resp = self.app.post('/post_pow2_opt')
        assert resp.text == '0', resp
