# -*- coding: utf-8 -*-
"""Tests for Predicates, mostly took from repoze.what test suite"""

##############################################################################
#
# Copyright (c) 2007, Agendaless Consulting and Contributors.
# Copyright (c) 2008, Florent Aide <florent.aide@gmail.com>.
# Copyright (c) 2008-2009, Gustavo Narea <me@gustavonarea.net>.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from nose.tools import raises
from webtest import TestApp
from tg._compat import u_, unicode_text

from tg import predicates, TGController, expose, config
from tg.configuration import AppConfig

class BasePredicateTester(object):
    """Base test case for predicates."""

    def assertEqual(self, val1, val2):
        assert val1 == val2, (val1, val2)

    def eval_met_predicate(self, p, environ):
        """Evaluate a predicate that should be met"""
        self.assertEqual(p.check_authorization(environ), None)
        self.assertEqual(p.is_met(environ), True)

    def eval_unmet_predicate(self, p, environ, expected_error):
        """Evaluate a predicate that should not be met"""
        credentials = environ.get('repoze.what.credentials')
        # Testing check_authorization
        try:
            p.evaluate(environ, credentials)
            self.fail('Predicate must not be met; expected error: %s' %
                      expected_error)
        except predicates.NotAuthorizedError as error:
            self.assertEqual(unicode_text(error), expected_error)
            # Testing is_met:
        self.assertEqual(p.is_met(environ), False)


#{ The test suite itself


class TestPredicate(BasePredicateTester):

    @raises(NotImplementedError)
    def test_evaluate_isnt_implemented(self):
        p = MockPredicate()
        p.evaluate(None, None)

    def test_message_is_changeable(self):
        previous_msg = EqualsTwo.message
        new_msg = 'It does not equal two!'
        p = EqualsTwo(msg=new_msg)
        self.assertEqual(new_msg, p.message)

    def test_message_isnt_changed_unless_required(self):
        previous_msg = EqualsTwo.message
        p = EqualsTwo()
        self.assertEqual(previous_msg, p.message)

    def test_unicode_messages(self):
        unicode_msg = u_('请登陆')
        p = EqualsTwo(msg=unicode_msg)
        environ = {'test_number': 3}
        self.eval_unmet_predicate(p, environ, unicode_msg)

    def test_authorized(self):
        environ = {'test_number': 4}
        p = EqualsFour()
        p.check_authorization(environ)

    def test_unauthorized(self):
        environ = {'test_number': 3}
        p = EqualsFour(msg="Go away!")
        try:
            p.check_authorization(environ)
            self.fail('Authorization must have been rejected')
        except predicates.NotAuthorizedError as e:
            self.assertEqual(str(e), "Go away!")

    def test_unauthorized_with_unicode_message(self):
        # This test is broken on Python 2.4 and 2.5 because the unicode()
        # function doesn't work when converting an exception into an unicode
        # string (this is, to extract its message).
        unicode_msg = u_('请登陆')
        environ = {'test_number': 3}
        p = EqualsFour(msg=unicode_msg)
        try:
            p.check_authorization(environ)
            self.fail('Authorization must have been rejected')
        except predicates.NotAuthorizedError as e:
            self.assertEqual(unicode_text(e), unicode_msg)

    def test_custom_failure_message(self):
        message = u_('This is a custom message whose id is: %(id_number)s')
        id_number = 23
        p = EqualsFour(msg=message)
        try:
            p.unmet(message, id_number=id_number)
            self.fail('An exception must have been raised')
        except predicates.NotAuthorizedError as e:
            self.assertEqual(unicode_text(e), message % dict(id_number=id_number))

    def test_credentials_dict_when_anonymous(self):
        """The credentials must be a dict even if the user is anonymous"""
        class CredentialsPredicate(predicates.Predicate):
            message = "Some text"
            def evaluate(self, environ, credentials):
                if 'something' in credentials:
                    self.unmet()
            # --- Setting the environ up
        environ = {}
        # --- Testing it:
        p = CredentialsPredicate()
        self.eval_met_predicate(p, environ)
        self.assertEqual(True, p.is_met(environ))

class TestContextRelatedBoolPredicate(BasePredicateTester):
    def setup(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return str(bool(EqualsTwo()))

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app()
        self.app = TestApp(app)

    def teardown(self):
        config.pop('tg.root_controller', None)

    def test_success(self):
        ans = self.app.get('/test', extra_environ={'test_number':'2'})
        assert 'True' in ans, ans

    def test_faillure(self):
        ans = self.app.get('/test', extra_environ={'test_number':'4'})
        assert 'False' in ans, ans

class TestCompoundPredicate(BasePredicateTester):

    def test_one_predicate_works(self):
        p = EqualsTwo()
        cp = predicates.CompoundPredicate(p)
        self.assertEqual(cp.predicates, (p,))

    def test_two_predicates_work(self):
        p1 = EqualsTwo()
        p2 = MockPredicate()
        cp = predicates.CompoundPredicate(p1, p2)
        self.assertEqual(cp.predicates, (p1, p2))


class TestNotPredicate(BasePredicateTester):

    def test_failure(self):
        environ = {'test_number': 4}
        # It must NOT equal 4
        p = predicates.Not(EqualsFour())
        # It equals 4!
        self.eval_unmet_predicate(p, environ, 'The condition must not be met')

    def test_failure_with_custom_message(self):
        environ = {'test_number': 4}
        # It must not equal 4
        p = predicates.Not(EqualsFour(), msg='It must not equal four')
        # It equals 4!
        self.eval_unmet_predicate(p, environ, 'It must not equal four')

    def test_success(self):
        environ = {'test_number': 5}
        # It must not equal 4
        p = predicates.Not(EqualsFour())
        # It doesn't equal 4!
        self.eval_met_predicate(p, environ)


class TestAllPredicate(BasePredicateTester):

    def test_one_true(self):
        environ = {'test_number': 2}
        p = predicates.All(EqualsTwo())
        self.eval_met_predicate(p, environ)

    def test_one_false(self):
        environ = {'test_number': 3}
        p = predicates.All(EqualsTwo())
        self.eval_unmet_predicate(p, environ, "Number 3 doesn't equal 2")

    def test_two_true(self):
        environ = {'test_number': 4}
        p = predicates.All(EqualsFour(), GreaterThan(3))
        self.eval_met_predicate(p, environ)

    def test_two_false(self):
        environ = {'test_number': 1}
        p = predicates.All(EqualsFour(), GreaterThan(3))
        self.eval_unmet_predicate(p, environ, "Number 1 doesn't equal 4")

    def test_two_mixed(self):
        environ = {'test_number': 5}
        p = predicates.All(EqualsFour(), GreaterThan(3))
        self.eval_unmet_predicate(p, environ, "Number 5 doesn't equal 4")


class TestAnyPredicate(BasePredicateTester):

    def test_one_true(self):
        environ = {'test_number': 2}
        p = predicates.Any(EqualsTwo())
        self.eval_met_predicate(p, environ)

    def test_one_false(self):
        environ = {'test_number': 3}
        p = predicates.Any(EqualsTwo())
        self.eval_unmet_predicate(p, environ,
            "At least one of the following predicates must be "
            "met: Number 3 doesn't equal 2")

    def test_two_true(self):
        environ = {'test_number': 4}
        p = predicates.Any(EqualsFour(), GreaterThan(3))
        self.eval_met_predicate(p, environ)

    def test_two_false(self):
        environ = {'test_number': 1}
        p = predicates.Any(EqualsFour(), GreaterThan(3))
        self.eval_unmet_predicate(p, environ,
            "At least one of the following predicates must be "
            "met: Number 1 doesn't equal 4, 1 is not greater "
            "than 3")

    def test_two_mixed(self):
        environ = {'test_number': 5}
        p = predicates.Any(EqualsFour(), GreaterThan(3))
        self.eval_met_predicate(p, environ)


class TestIsUserPredicate(BasePredicateTester):

    def test_user_without_credentials(self):
        environ = {}
        p = predicates.is_user('gustavo')
        self.eval_unmet_predicate(p, environ,
            'The current user must be "gustavo"')

    def test_user_without_userid(self):
        environ = {'repoze.what.credentials': {}}
        p = predicates.is_user('gustavo')
        self.eval_unmet_predicate(p, environ,
            'The current user must be "gustavo"')

    def test_right_user(self):
        environ = make_environ('gustavo')
        p = predicates.is_user('gustavo')
        self.eval_met_predicate(p, environ)

    def test_wrong_user(self):
        environ = make_environ('andreina')
        p = predicates.is_user('gustavo')
        self.eval_unmet_predicate(p, environ,
            'The current user must be "gustavo"')


class TestInGroupPredicate(BasePredicateTester):

    def test_user_belongs_to_group(self):
        environ = make_environ('gustavo', ['developers'])
        p = predicates.in_group('developers')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_belong_to_group(self):
        environ = make_environ('gustavo', ['developers', 'admins'])
        p = predicates.in_group('designers')
        self.eval_unmet_predicate(p, environ,
            'The current user must belong to the group "designers"')


class TestInAllGroupsPredicate(BasePredicateTester):

    def test_user_belongs_to_groups(self):
        environ = make_environ('gustavo', ['developers', 'admins'])
        p = predicates.in_all_groups('developers', 'admins')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_belong_to_groups(self):
        environ = make_environ('gustavo', ['users', 'admins'])
        p = predicates.in_all_groups('developers', 'designers')
        self.eval_unmet_predicate(p, environ,
            'The current user must belong to the group "developers"')

    def test_user_doesnt_belong_to_one_group(self):
        environ = make_environ('gustavo', ['developers'])
        p = predicates.in_all_groups('developers', 'designers')
        self.eval_unmet_predicate(p, environ,
            'The current user must belong to the group "designers"')


class TestInAnyGroupsPredicate(BasePredicateTester):

    def test_user_belongs_to_groups(self):
        environ = make_environ('gustavo', ['developers',' admins'])
        p = predicates.in_any_group('developers', 'admins')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_belong_to_groups(self):
        environ = make_environ('gustavo', ['users', 'admins'])
        p = predicates.in_any_group('developers', 'designers')
        self.eval_unmet_predicate(p, environ,
            'The member must belong to at least one of the '
            'following groups: developers, designers')

    def test_user_doesnt_belong_to_one_group(self):
        environ = make_environ('gustavo', ['designers'])
        p = predicates.in_any_group('developers', 'designers')
        self.eval_met_predicate(p, environ)


class TestIsAnonymousPredicate(BasePredicateTester):

    def test_authenticated_user(self):
        environ = make_environ('gustavo')
        p = predicates.is_anonymous()
        self.eval_unmet_predicate(p, environ,
            'The current user must be anonymous')

    def test_anonymous_user(self):
        environ = {}
        p = predicates.is_anonymous()
        self.eval_met_predicate(p, environ)


class TestNotAnonymousPredicate(BasePredicateTester):

    def test_authenticated_user(self):
        environ = make_environ('gustavo')
        p = predicates.not_anonymous()
        self.eval_met_predicate(p, environ)

    def test_anonymous_user(self):
        environ = {}
        p = predicates.not_anonymous()
        self.eval_unmet_predicate(p, environ,
            'The current user must have been authenticated')


class TestHasPermissionPredicate(BasePredicateTester):

    def test_user_has_permission(self):
        environ = make_environ('gustavo', permissions=['watch-tv'])
        p = predicates.has_permission('watch-tv')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_have_permission(self):
        environ = make_environ('gustavo', permissions=['watch-tv'])
        p = predicates.has_permission('eat')
        self.eval_unmet_predicate(p, environ,
            'The user must have the "eat" permission')


class TestHasAllPermissionsPredicate(BasePredicateTester):

    def test_user_has_all_permissions(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_all_permissions('watch-tv', 'eat')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_have_permissions(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_all_permissions('jump', 'scream')
        self.eval_unmet_predicate(p, environ,
            'The user must have the "jump" permission')

    def test_user_has_one_permission(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_all_permissions('party', 'scream')
        self.eval_unmet_predicate(p, environ,
            'The user must have the "scream" permission')


class TestUserHasAnyPermissionsPredicate(BasePredicateTester):

    def test_user_has_all_permissions(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_any_permission('watch-tv', 'eat')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_have_all_permissions(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_any_permission('jump', 'scream')
        self.eval_unmet_predicate(p, environ,
            'The user must have at least one of the following '
            'permissions: jump, scream')

    def test_user_has_one_permission(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_any_permission('party', 'scream')
        self.eval_met_predicate(p, environ)


#{ Test utilities


def make_environ(user, groups=None, permissions=None):
    """Make a WSGI enviroment with the credentials dict"""
    credentials = {'repoze.what.userid': user}
    credentials['groups'] = groups or []
    credentials['permissions'] = permissions or []
    environ = {'repoze.what.credentials': credentials}
    return environ


#{ Mock definitions


class MockPredicate(predicates.Predicate):
    message = "I'm a fake predicate"

class EqualsTwo(predicates.Predicate):
    message = "Number %(number)s doesn't equal 2"

    def evaluate(self, environ, credentials):
        number = environ.get('test_number')
        if not number or int(number) != 2:
            self.unmet(number=number)


class EqualsFour(predicates.Predicate):
    message = "Number %(number)s doesn't equal 4"

    def evaluate(self, environ, credentials):
        number = environ.get('test_number')
        if number == 4:
            return
        self.unmet(number=number)


class GreaterThan(predicates.Predicate):
    message = "%(number)s is not greater than %(compared_number)s"

    def __init__(self, compared_number, **kwargs):
        super(GreaterThan, self).__init__(**kwargs)
        self.compared_number = compared_number

    def evaluate(self, environ, credentials):
        number = environ.get('test_number')
        if not number > self.compared_number:
            self.unmet(number=number, compared_number=self.compared_number)


class LessThan(predicates.Predicate):
    message = "%(number)s must be less than %(compared_number)s"

    def __init__(self, compared_number, **kwargs):
        super(LessThan, self).__init__(**kwargs)
        self.compared_number = compared_number

    def evaluate(self, environ, credentials):
        number = environ.get('test_number')
        if not number < self.compared_number:
            self.unmet(number=number, compared_number=self.compared_number)

