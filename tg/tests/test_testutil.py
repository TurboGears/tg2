"""Tests for the testutil module"""

from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
import transaction

from tg.testutil import DBTest
from tg.tests.fixtures import model


# Ideally, we would have defined several different descendants of DBTest,
# in order to test its behavior in different situations, but there seem to be
# a problem in unittests and grand-grandchildren of TestCase won't work. You
# may try this code if you want: http://paste.turbogears.org/paste/4721
# or http://paste.turbogears.org/paste/4724

class BaseModelTest(DBTest):
    database = create_engine("sqlite:///:memory:")
    model = model


class TestGroup(BaseModelTest):
    """Test case for the Group model.
    
    This should tell us whether the setUp() and tearDown() of DBTest work as
    expected.
    
    """
    
    def test_group_creation(self):
        group = model.Group()
        group.group_name = u"turbogears"
        group.display_name = u"The TurboGears Team"
        model.DBSession.add(group)
        model.DBSession.flush()
        transaction.commit()
    
    def test_this_group_was_already_removed(self):
        group = model.Group()
        group.group_name = u"turbogears"
        group.display_name = u"The TurboGears Team"
        model.DBSession.add(group)
        model.DBSession.flush()
        transaction.commit()
