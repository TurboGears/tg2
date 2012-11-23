# -*- coding: utf-8 -*-
"""
Built-in predicate checkers.

This is mostly took from repoze.what.precidates

This is module provides the predicate checkers that were present in the
original "identity" framework of TurboGears 1, plus others.

"""

from __future__ import unicode_literals
from tg import request
from tg._compat import unicode_text

__all__ = ['Predicate', 'CompoundPredicate', 'All', 'Any',
           'has_all_permissions', 'has_any_permission', 'has_permission',
           'in_all_groups', 'in_any_group', 'in_group', 'is_user',
           'is_anonymous', 'not_anonymous', 'NotAuthorizedError']

try: #pragma: no cover
    # If repoze.what is available use repoze.what Predicate and
    # NotAuthorizedError adding booleanization support to the
    # predicates
    from repoze.what.predicates import NotAuthorizedError, Predicate
    Predicate.__nonzero__ = lambda self: self.is_met(request.environ)
except ImportError:
    class NotAuthorizedError(Exception):
        pass

    class Predicate(object):
        def __init__(self, msg=None):
            if msg:
                self.message = msg

        def evaluate(self, environ, credentials):
            raise NotImplementedError

        def unmet(self, msg=None, **placeholders):
            """
            Raise an exception because this predicate is not met.

            :param msg: The error message to be used; overrides the predicate's
                default one.
            :type msg: str
            :raises NotAuthorizedError: If the predicate is not met.

            ``placeholders`` represent the placeholders for the predicate message.
            The predicate's attributes will also be taken into account while
            creating the message with its placeholders.
            """
            if msg:
                message = msg
            else:
                message = self.message

            # This enforces lazy strings resolution (lazy translation for example)
            message = unicode_text(message)

            # Include the predicate attributes in the placeholders:
            all_placeholders = self.__dict__.copy()
            all_placeholders.update(placeholders)

            raise NotAuthorizedError(message % all_placeholders)

        def check_authorization(self, environ):
            """
            Evaluate the predicate and raise an exception if it's not met.

            :param environ: The WSGI environment.
            :raise NotAuthorizedError: If it the predicate is not met.
            """
            credentials = environ.get('repoze.what.credentials', {})
            try:
                self.evaluate(environ, credentials)
            except NotAuthorizedError:
                raise

        def is_met(self, environ):
            """
            Find whether the predicate is met or not.

            :param environ: The WSGI environment.
            :return: Whether the predicate is met or not.
            :rtype: bool
            """
            credentials = environ.get('repoze.what.credentials', {})
            try:
                self.evaluate(environ, credentials)
                return True
            except NotAuthorizedError:
                return False

        def __nonzero__(self):
            return self.is_met(request.environ)
        __bool__ = __nonzero__

class CompoundPredicate(Predicate):
    """A predicate composed of other predicates."""

    def __init__(self, *predicates, **kwargs):
        super(CompoundPredicate, self).__init__(**kwargs)
        self.predicates = predicates


class Not(Predicate):
    """
    Negate the specified predicate.

    :param predicate: The predicate to be negated.

    Example::

        # The user *must* be anonymous:
        p = Not(not_anonymous())

    """
    message = "The condition must not be met"

    def __init__(self, predicate, **kwargs):
        super(Not, self).__init__(**kwargs)
        self.predicate = predicate

    def evaluate(self, environ, credentials):
        try:
            self.predicate.evaluate(environ, credentials)
        except NotAuthorizedError:
            return
        self.unmet()


class All(CompoundPredicate):
    """
    Check that all of the specified predicates are met.

    :param predicates: All of the predicates that must be met.

    Example::

        # Grant access if the current month is July and the user belongs to
        # the human resources group.
        p = All(is_month(7), in_group('hr'))

    """

    def evaluate(self, environ, credentials):
        """
        Evaluate all the predicates it contains.

        :param environ: The WSGI environment.
        :param credentials: The :mod:`repoze.what` ``credentials``.
        :raises NotAuthorizedError: If one of the predicates is not met.

        """
        for p in self.predicates:
            p.evaluate(environ, credentials)


class Any(CompoundPredicate):
    """
    Check that at least one of the specified predicates is met.

    :param predicates: Any of the predicates that must be met.

    Example::

        # Grant access if the currest user is Richard Stallman or Linus
        # Torvalds.
        p = Any(is_user('rms'), is_user('linus'))

    """
    message = "At least one of the following predicates must be met: %(failed_predicates)s"

    def evaluate(self, environ, credentials):
        """
        Evaluate all the predicates it contains.

        :param environ: The WSGI environment.
        :param credentials: The :mod:`repoze.what` ``credentials``.
        :raises NotAuthorizedError: If none of the predicates is met.

        """
        errors = []
        for p in self.predicates:
            try:
                p.evaluate(environ, credentials)
                return
            except NotAuthorizedError as exc:
                errors.append(unicode_text(exc))
        failed_predicates = ', '.join(errors)
        self.unmet(failed_predicates=failed_predicates)


class is_user(Predicate):
    """
    Check that the authenticated user's username is the specified one.

    :param user_name: The required user name.
    :type user_name: str

    Example::

        p = is_user('linus')

    """

    message = 'The current user must be "%(user_name)s"'

    def __init__(self, user_name, **kwargs):
        super(is_user, self).__init__(**kwargs)
        self.user_name = user_name

    def evaluate(self, environ, credentials):
        if credentials and\
           self.user_name == credentials.get('repoze.what.userid'):
            return
        self.unmet()


class in_group(Predicate):
    """
    Check that the user belongs to the specified group.

    :param group_name: The name of the group to which the user must belong.
    :type group_name: str

    Example::

        p = in_group('customers')

    """

    message = 'The current user must belong to the group "%(group_name)s"'

    def __init__(self, group_name, **kwargs):
        super(in_group, self).__init__(**kwargs)
        self.group_name = group_name

    def evaluate(self, environ, credentials):
        if credentials and self.group_name in credentials.get('groups'):
            return
        self.unmet()


class in_all_groups(All):
    """
    Check that the user belongs to all of the specified groups.

    :param groups: The name of all the groups the user must belong to.

    Example::

        p = in_all_groups('developers', 'designers')

    """


    def __init__(self, *groups, **kwargs):
        group_predicates = [in_group(g) for g in groups]
        super(in_all_groups,self).__init__(*group_predicates, **kwargs)


class in_any_group(Any):
    """
    Check that the user belongs to at least one of the specified groups.

    :param groups: The name of any of the groups the user may belong to.

    Example::

        p = in_any_group('directors', 'hr')

    """

    message = "The member must belong to at least one of the following groups: %(group_list)s"

    def __init__(self, *groups, **kwargs):
        self.group_list = ", ".join(groups)
        group_predicates = [in_group(g) for g in groups]
        super(in_any_group,self).__init__(*group_predicates, **kwargs)


class is_anonymous(Predicate):
    """
    Check that the current user is anonymous.

    Example::

        # The user must be anonymous!
        p = is_anonymous()

    .. versionadded:: 1.0.7

    """

    message = "The current user must be anonymous"

    def evaluate(self, environ, credentials):
        if credentials:
            self.unmet()


class not_anonymous(Predicate):
    """
    Check that the current user has been authenticated.

    Example::

        # The user must have been authenticated!
        p = not_anonymous()

    """

    message = "The current user must have been authenticated"

    def evaluate(self, environ, credentials):
        if not credentials:
            self.unmet()


class has_permission(Predicate):
    """
    Check that the current user has the specified permission.

    :param permission_name: The name of the permission that must be granted to
        the user.

    Example::

        p = has_permission('hire')

    """
    message = 'The user must have the "%(permission_name)s" permission'

    def __init__(self, permission_name, **kwargs):
        super(has_permission, self).__init__(**kwargs)
        self.permission_name = permission_name

    def evaluate(self, environ, credentials):
        if credentials and\
           self.permission_name in credentials.get('permissions'):
            return
        self.unmet()


class has_all_permissions(All):
    """
    Check that the current user has been granted all of the specified
    permissions.

    :param permissions: The names of all the permissions that must be
        granted to the user.

    Example::

        p = has_all_permissions('view-users', 'edit-users')

    """

    def __init__(self, *permissions, **kwargs):
        permission_predicates = [has_permission(p) for p in permissions]
        super(has_all_permissions, self).__init__(*permission_predicates,
            **kwargs)


class has_any_permission(Any):
    """
    Check that the user has at least one of the specified permissions.

    :param permissions: The names of any of the permissions that have to be
        granted to the user.

    Example::

        p = has_any_permission('manage-users', 'edit-users')

    """

    message = "The user must have at least one of the following permissions: %(permission_list)s"

    def __init__(self, *permissions, **kwargs):
        self.permission_list = ", ".join(permissions)
        permission_predicates = [has_permission(p) for p in permissions]
        super(has_any_permission,self).__init__(*permission_predicates,
            **kwargs)