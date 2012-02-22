# -*- coding: utf-8 -*-

from nose.tools import raises

import pylons
from formencode import validators, Schema
from simplejson import loads

from tg.controllers import TGController
from tg.decorators import expose, validate, before_render
from tests.base import (TestWSGIController, data_dir,
    make_app, setup_session_dir, teardown_session_dir)

from tw.forms import TableForm, TextField
from tw.api import WidgetsList

def setup():
    setup_session_dir()

def teardown():
    teardown_session_dir()

class MyForm(TableForm):

    class fields(WidgetsList):
        """This WidgetsList is just a container."""
        title=TextField(validator = validators.NotEmpty())
        year = TextField(size=4, validator=validators.Int())

# then, we create an instance of this form
myform = MyForm("my_form", action='create')


class Pwd(Schema):
    pwd1 = validators.String(not_empty=True)
    pwd2 = validators.String(not_empty=True)
    chained_validators = [validators.FieldsMatch('pwd1', 'pwd2')]


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

class BasicTGController(TGController):

    @expose('json')
    @validate(validators={"some_int": validators.Int()})
    def validated_int(self, some_int):
        assert isinstance(some_int, int)
        return dict(response=some_int)

    @expose('json')
    @validate(validators={"a": validators.Int()})
    def validated_and_unvalidated(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode)
        return dict(int=a, str=b)

    @expose()
    @controller_based_validate()
    def validate_controller_based_validator(self, *args, **kw):
        return 'ok'

    @expose('json')
    @validate(validators={"a": validators.Int(), "someemail": validators.Email})
    def two_validators(self, a=None, someemail=None, *args):
        errors = pylons.tmpl_context.form_errors
        values =  pylons.tmpl_context.form_values
        return dict(a=a, someemail=someemail,
                errors=str(errors), values=str(values))

    @expose('json')
    @validate(validators={"a": validators.Int()})
    def with_default_shadow(self, a, b=None ):
        """A default value should not cause the validated value to disappear"""
        assert isinstance( a, int ), type(a)
        return {
            'int': a,
        }

    @expose('json')
    @validate(validators={"e": ColonValidator()})
    def error_with_colon(self, e):
        errors = pylons.tmpl_context.form_errors
        return dict(errors=str(errors))

    @expose('json')
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

    @expose('json')
    @validate(form=myform)
    def process_form(self, **kwargs):
        kwargs['errors'] = pylons.tmpl_context.form_errors
        return dict(kwargs)

    @expose('json')
    @validate(form=myform, error_handler=process_form)
    def send_to_error_handler(self, **kwargs):
        kwargs['errors'] = pylons.tmpl_context.form_errors
        return dict(kwargs)

    @expose()
    def set_lang(self, lang=None):
        pylons.session['tg_lang'] = lang
        pylons.session.save()
        return 'ok'

    @expose()
    @validate(validators=Pwd())
    def password(self, pwd1, pwd2):
        if pylons.tmpl_context.form_errors:
            return "There was an error"
        else:
            return "Password ok!"

    @expose('json')
    @before_render(lambda rem,params,output:output.update({'GOT_ERROR':'HOOKED'}))
    def hooked_error_handler(self, *args, **kw):
        return dict(GOT_ERROR='MISSED HOOK')

    @expose()
    @validate({'v':validators.Int()}, error_handler=hooked_error_handler)
    def with_hooked_error_handler(self, *args, **kw):
        return dict(GOT_ERROR='NO ERROR')

class TestTGController(TestWSGIController):

    def setUp(self):
        TestWSGIController.setUp(self)
        pylons.config.update({
            'pylons.paths': {'root': data_dir},
            'pylons.package': 'tests'})
        self.app = make_app(BasicTGController)

    def test_basic_validation_and_jsonification(self):
        """Ensure you can pass in a dictionary of validators"""
        form_values = {"some_int": 22}
        resp = self.app.post('/validated_int', form_values)
        assert '{"response": 22}'in resp, resp

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
        content = loads(resp.body)
        assert content['a'] == 1

    def test_validation_errors(self):
        """Ensure that dict validation produces a full set of errors"""
        form_values = {'a': '1', 'someemail': "guido~google.com"}
        resp = self.app.post('/two_validators', form_values)
        content = loads(resp.body)
        errors = content.get('errors', None)
        assert errors, 'There should have been at least one error'
        assert 'someemail' in errors, \
            'The email was invalid and should have been reported in the errors'

    def test_form_validation(self):
        """Check @validate's handing of ToscaWidget forms instances"""
        form_values = {'title': 'Razer', 'year': "2007"}
        resp = self.app.post('/process_form', form_values)
        values = loads(resp.body)
        assert values['year'] == 2007

    def test_error_with_colon(self):
        resp = self.app.post('/error_with_colon', {'e':"fakeparam"})
        assert 'Description' in resp.body, resp.body       

    def test_form_render(self):
        """Test that myform renders properly"""
        resp = self.app.post('/display_form')
        assert 'id="my_form_title.label"' in resp, resp
        assert 'class="fieldlabel required"' in resp, resp
        assert "Title" in resp, resp

    def test_form_validation_error(self):
        """Test form validation with error message"""
        form_values = {'title': 'Razer', 'year': "t007"}
        resp = self.app.post('/process_form', form_values)
        values = loads(resp.body)
        assert "Please enter an integer value" in values['errors']['year'], \
            'Error message not found: %r' % values['errors']

    def test_form_validation_redirect(self):
        """Test form validation error message with redirect"""
        form_values = {'title': 'Razer', 'year': "t007"}
        resp = self.app.post('/send_to_error_handler', form_values)
        values = loads(resp.body)
        assert "Please enter an integer value" in values['errors']['year'], \
            'Error message not found: %r' % values['errors']

    def test_form_validation_translation(self):
        """Test translation of form validation error messages"""
        form_values = {'title': 'Razer', 'year': "t007"}
        # check with language set in request header
        resp = self.app.post('/process_form', form_values,
            headers={'Accept-Language': 'de,ru,it'})
        values = loads(resp.body)
        assert u"Bitte eine ganze Zahl eingeben" in values['errors']['year'], \
            'No German error message: %r' % values['errors']
        resp = self.app.post('/process_form', form_values,
            headers={'Accept-Language': 'ru,de,it'})
        values = loads(resp.body)
        assert u"Введите числовое значение" in values['errors']['year'], \
            'No Russian error message: %r' % values['errors']
        # check with language set in session
        self.app.post('/set_lang/de')
        resp = self.app.post('/process_form', form_values,
            headers={'Accept-Language': 'ru,it'})
        values = loads(resp.body)
        assert u"Bitte eine ganze Zahl eingeben" in values['errors']['year'], \
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