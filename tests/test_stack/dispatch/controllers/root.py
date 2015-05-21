# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import tg
from tg.controllers import TGController
from tg.decorators import expose, validate, https, variable_decode, with_trailing_slash, \
    without_trailing_slash, with_engine
from tg import expose, redirect, config
from tg.controllers import TGController
from tg import dispatched_controller
from nose.tools import eq_
from tests.test_validation import validators
from tg._compat import unicode_text

from paste.deploy.converters import asbool

class NestedSubController(TGController):
    @expose()
    def index(self):
        return '-'.join((self.mount_point, dispatched_controller().mount_point))

    @expose()
    def hitme(self):
        return '*'.join((self.mount_point, dispatched_controller().mount_point))

    @expose()
    def _lookup(self, *args):
        lookup = LookupController()
        return lookup, args

class SubController(TGController):
    nested = NestedSubController()
    
    @expose()
    def foo(self,):
        return 'sub_foo'

    @expose()
    def index(self):
        return 'sub index'

    @expose()
    def _default(self, *args):
        return ("recieved the following args (from the url): %s" %list(args))

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, **kw)

    @expose()
    def redirect_sub(self):
        tg.redirect('index')

    @expose()
    def redirect_list(self):
        tg.redirect(["/sub2", "list"])

    @expose()
    def hello(self, name):
        return "Why HELLO! " + name

    @expose()
    def hitme(self):
        return '@'.join((self.mount_point, dispatched_controller().mount_point))

class LookupController(TGController):
    nested = NestedSubController()
    
    @expose()
    def findme(self, *args, **kw):
        return 'got to lookup'

    @expose()
    def hiddenhitme(self, *args, **kw):
        return ' '.join((self.mount_point, dispatched_controller().mount_point))

class SubController2(object):
    @expose()
    def index(self):
        tg.redirect('list')

    @expose()
    def list(self, **kw):
        return "hello list"

    @expose()
    def _lookup(self, *args):
        lookup = LookupController()
        return lookup, args

class RootController(TGController):
    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose()
    def _default(self, remainder):
        return "Main Default Page called for url /%s"%remainder

    @expose()
    def feed(self, feed=None):
        return feed

    sub = SubController()
    sub2 = SubController2()

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, kw)

    @expose()
    def hello(self, name, silly=None):
        return "Hello " + name

    @expose()
    def redirect_cookie(self, name):
        tg.response.set_cookie('name', name)
        tg.redirect('/hello_cookie')

    @expose()
    def hello_cookie(self):
        return "Hello " + tg.request.cookies['name']

    @expose()
    def flash_redirect(self):
        tg.flash("Wow, <br/>flash!")
        tg.redirect("/flash_after_redirect")

    @expose()
    def flash_render(self, using_js=False, with_message=True):
        if asbool(with_message):
            tg.flash('JS <br/>Flash')

        return tg.flash.render('flash', asbool(using_js))

    @expose()
    def bigflash_redirect(self):
        tg.flash('x' * 5000)
        tg.redirect('/flash_after_redirect')

    @expose()
    def flash_unicode(self):
        tg.flash("Привет, мир!")
        tg.redirect("/flash_after_redirect")

    @expose()
    def flash_after_redirect(self):
        return tg.get_flash()

    @expose()
    def flash_status(self):
        return tg.get_status()

    @expose()
    def flash_no_redirect(self):
        tg.flash("Wow, flash!")
        return tg.get_flash()

    @expose('json')
    @validate(validators={"some_int": validators.Int()})
    def validated_int(self, some_int):
        assert isinstance(some_int, int)
        return dict(response=some_int)

    @expose('json')
    @validate(validators={"a":validators.Int()})
    def validated_and_unvalidated(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode_text)
        return dict(int=a,str=b)

    @expose()
    @expose('json')
    def stacked_expose(self, tg_format=None):
        return dict(got_json=True)

    @expose('json')
    def json_return_list(self):
        return [1,2,3]

    @expose(content_type='image/png')
    def custom_content_type(self):
        return b'PNG'

    @expose()
    def custom_content_type2(self):
        tg.response.content_type = 'image/png'
        return b'PNG2'

    @expose(content_type='text/plain')
    def custom_content_text_plain_type(self):
        return 'a<br/>bx'

    @expose()
    def check_params(self, *args, **kwargs):
        if not args and not kwargs:
            return "None recieved"
        else:
            return "Controler recieved: %s, %s" %(args, kwargs)

    @expose()
    def test_url_sop(self):
        from tg import url
        eq_('/foo', url('/foo'))


        u = url("/foo", params=dict(bar=1, baz=2))
        assert u in \
                ["/foo?bar=1&baz=2", "/foo?baz=2&bar=1"], u

    @https
    @expose()
    def test_https(self, **kw):
        return ''

    @expose('json')
    @variable_decode
    def test_vardec(self, **kw):
        return kw

    @expose('mako:echo.mak')
    def echo(self):
        return dict()

    @expose()
    @with_trailing_slash
    def with_tslash(self):
        return 'HI'

    @expose()
    @without_trailing_slash
    def without_tslash(self):
        return 'HI'

    @expose()
    @with_engine('mainslave', master_params=['first'])
    def onmaster_withlist(self, **kw):
        return '%s-%s' % (tg.request._tg_force_sqla_engine, kw)

    @expose()
    @with_engine('mainslave', master_params={'first':True, 'second':False})
    def onmaster(self, **kw):
        return '%s-%s' % (tg.request._tg_force_sqla_engine, kw)