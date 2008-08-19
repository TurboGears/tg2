"""Tests for the testutil module"""

from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
import transaction

from tg.testutil import DBTest
from tg.tests.fixtures import model

class BaseDBTest(DBTest):
    """This is the same as DBTest, except that its parent is not called.
    
    It just sets the parameter call_dad to False, so that we can test this
    class; it'd be impossible to test it otherwise.
    
    """
    def __init__(self, *args, **kwargs):
        super(BaseDBTest, self).__init__(False, *args, **kwargs)


class EmptyTestCase(BaseDBTest):
    pass


class DatabaseYesModelNo(BaseDBTest):
    database = create_engine("sqlite:///:memory:")


class DatabaseNoModelYes(BaseDBTest):
    model = model


class ValidDBTest(BaseDBTest):
    database = create_engine("sqlite:///:memory:")
    model = model


class TestDatabaseBaseTesting(TestCase):
    """Test case for DBTest"""
    
    def _create_row(self, value, test):
        model.init_model(ValidDBTest.database)
        test.setUp()
        
        grp = model.Group()
        grp.group_name = value
    
        model.DBSession.save(grp)
        model.DBSession.flush()
        transaction.commit()
    
    def test_no_database_no_model(self):
        """The database and model to be tested must be defined"""
        self.assertRaises(AssertionError, EmptyTestCase)
    
    def test_no_database(self):
        """The database to be tested must be defined"""
        self.assertRaises(AssertionError, DatabaseYesModelNo)
    
    def test_no_model(self):
        """The model to be tested must be defined"""
        self.assertRaises(AssertionError, DatabaseNoModelYes)
    
    def test_valid_descendant(self):
        """Everything is OK if and only if both the database and the model
        are defined"""
        ValidDBTest()
    
    def test_setup(self):
        """After the setup I must be able to insert rows"""
        test = ValidDBTest()
        self._create_row("developers", test)
    
    def test_teardown(self):
        """After the tearDown the tables must not exist"""
        test = ValidDBTest()
        self._create_row("directors", test)
        test.tearDown()
        
        self.assertRaises(DBAPIError,
                          model.DBSession.query(model.Group).filter(
                                model.Group.group_name=="directors").first
                          )
    