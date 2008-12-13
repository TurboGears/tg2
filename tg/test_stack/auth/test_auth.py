# -*- coding: utf-8 -*-
"""
Tests for the integration of repoze.who and repoze.what into TG.

"""

import tg, pylons
from tg.controllers import TGController
from tg.decorators import expose, require
from repoze.what import predicates
from nose.tools import eq_

from auth_base import TestWSGIController, make_app, setup_session_dir, \
                      teardown_session_dir


def setup():
    setup_session_dir()


def _teardown():
    teardown_session_dir()


class SubController1(TGController):
    """Mock TG2 subcontroller"""
    
    @expose()
    def index(self):
        return 'hello sub1'
    
    @expose()
    def in_group(self):
        return 'in group'


class SecurePanel(TGController):
    """Mock TG2 secure controller"""
    
    _require = predicates.has_permission('edit-site')
    
    @expose()
    def index(self):
        return 'you have the permission'
    
    @expose()
    @require(predicates.in_group('developers'))
    def commit(self):
        return 'you can commit'
    
    @expose()
    @require(predicates.in_group('admins'))
    def delete_user(self):
        return 'you can delete users'


class BasicTGController(TGController):
    """Mock TG2 controller"""

    sub1 = SubController1()
    
    panel = SecurePanel()
    
    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose()
    def default(self, remainder):
        return "Main Default Page called for url /%s" % remainder
    
    @expose()
    @require(predicates.in_group('admins'))
    def admin(self):
        return 'got to admin'
    
    @expose()
    @require(predicates.in_all_groups('developers', 'admins'))
    def all_groups(self):
        return 'got to all groups'

    @expose()
    @require(predicates.in_any_group('php', 'trolls'))
    def any_groups(self):
        return 'got to any groups'

    @expose()
    @require(predicates.is_user('rms'))
    def rms_user(self):
        return 'got to promote freedomware'
    
    @expose()
    @require(predicates.has_permission('edit-site'))
    def editsite_perm_only(self):
        return 'got to edit'
    
    @expose()
    @require(predicates.has_any_permission('commit'))
    def commit_perm(self):
        return 'got to commit'

    @expose()
    @require(predicates.has_all_permissions('commit', 'edit-site'))
    def all_perm(self):
        return 'got to all perm'

    @expose()
    @require(predicates.not_anonymous())
    def not_anon(self):
        return 'got to not anon'
    
    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, kw)


class TestTGController(TestWSGIController):
    """Test case for the mock TG controller and its subcontroller"""
    
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)
    
    def _test_index(self):
        resp = self.app.get('/index/')
        assert 'hello' in resp.body
    
    def test_group_no_auth(self):
        resp = self.app.get('/admin')
        assert resp.body.startswith('302 Found'), resp.body
    
    def test_group_with_auth(self):
        resp = self.app.get('/login_handler?login=rms&password=freedom')
        resp = self.app.get('/admin')
        eq_(resp.body, 'got to admin')

    def test_all_groups_no_auth(self):
        resp = self.app.get('/login_handler?login=rasmus&password=php')
        resp = self.app.get('/all_groups')
        assert resp.body.startswith('302 Found'), resp.body
    
    def test_all_groups(self):
        resp = self.app.get('/login_handler?login=rms&password=freedom')
        resp = self.app.get('/all_groups')
        eq_(resp.body, 'got to all groups')

    def test_any_groups_no_auth(self):
        resp = self.app.get('/login_handler?login=linus&password=freedomware')
        resp = self.app.get('/any_groups')
        assert resp.body.startswith('302 Found'), resp.body
    
    def test_any_groups(self):
        resp = self.app.get('/login_handler?login=sballmer&password=developers')
        resp = self.app.get('/any_groups')
        eq_(resp.body, 'got to any groups')

    def test_no_auth_not_anon(self):
        resp = self.app.get('/not_anon')
        assert resp.body.startswith('302 Found'), resp.body

    def test_not_anon(self):
        resp = self.app.get('/login_handler?login=linus&password=linux')
        resp = self.app.get('/not_anon')
        eq_(resp.body, 'got to not anon')

    def test_no_auth_is_user(self):
        resp = self.app.get('/login_handler?login=sballmer&password=developers')
        resp = self.app.get('/rms_user')
        assert resp.body.startswith('302 Found'), resp.body

    def test_is_user(self):
        resp = self.app.get('/login_handler?login=rms&password=freedom')
        resp = self.app.get('/rms_user')
        eq_(resp.body, 'got to promote freedomware')

    def test_no_auth_perm(self):
        resp = self.app.get('/login_handler?login=sballmer&password=developers')
        resp = self.app.get('/editsite_perm_only')
        assert resp.body.startswith('302 Found'), resp.body

    def test_perm(self):
        resp = self.app.get('/login_handler?login=rms&password=freedom')
        resp = self.app.get('/editsite_perm_only')
        eq_(resp.body, 'got to edit')

    def test_no_auth_any_perm(self):
        resp = self.app.get('/login_handler?login=linus&password=freedomware')
        resp = self.app.get('/commit_perm')
        assert resp.body.startswith('302 Found'), resp.body

    def test_any_perm(self):
        resp = self.app.get('/login_handler?login=rms&password=freedom')
        resp = self.app.get('/commit_perm')
        eq_(resp.body, 'got to commit')

    def test_no_auth_all_perm(self):
        resp = self.app.get('/login_handler?login=linus&password=freedomware')
        resp = self.app.get('/all_perm')
        assert resp.body.startswith('302 Found'), resp.body

    def test_all_perm(self):
        resp = self.app.get('/login_handler?login=linus&password=linux')
        resp = self.app.get('/all_perm')
        eq_(resp.body, 'got to all perm')
        
    def test_sub_in_admin(self):
        resp = self.app.get('/login_handler?login=sballmer&password=developers')
        resp = self.app.get('/sub1/in_group')
        eq_(resp.body, 'in group')
    
    def test_controller_wide_authorization_when_allowed(self):
        resp = self.app.get('/login_handler?login=rms&password=freedom')
        resp = self.app.get('/panel')
        eq_(resp.body, 'you have the permission')
    
    def test_controller_wide_authorization_when_denied(self):
        resp = self.app.get('/login_handler?login=sballmer&password=developers')
        resp = self.app.get('/panel')
        assert resp.body.startswith('302 Found'), resp.body
    
    def test_controller_authorization_with_require_decorator_when_allowed(self):
        resp = self.app.get('/login_handler?login=linus&password=linux')
        resp = self.app.get('/panel/commit')
        eq_(resp.body, 'you can commit')
    
    def test_controller_authorization_with_require_decorator_when_denied(self):
        resp = self.app.get('/login_handler?login=linus&password=linux')
        resp = self.app.get('/panel/delete_user')
        assert resp.body.startswith('302 Found'), resp.body
