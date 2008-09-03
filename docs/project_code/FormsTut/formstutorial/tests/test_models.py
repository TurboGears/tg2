# -*- coding: utf-8 -*-
"""Test suite for the TG app's models"""

from tg.testutil import DBTest
from sqlalchemy import create_engine

from formstutorial import model

test_database = create_engine("sqlite:///:memory:")

class TestModel(DBTest):
    """The base class for testing models in you TG project."""
    model = model
    database = test_database

    
class TestUser(TestModel):
    """Test case for the User model."""
    
    def setUp(self):
        super(TestUser, self).setUp()
        self.member = model.User()
        self.member.user_name = u"ignucius"
        self.member.email_address = u"ignucius@example.org"
        
    def test_member_creation_username(self):
        """The member constructor must set the user name right"""
        self.assertEqual(self.member.user_name, u"ignucius")
        
    def test_member_creation_email(self):
        """The member constructor must set the email right"""
        self.assertEqual(self.member.email_address, u"ignucius@example.org")
    
    def test_no_permissions_by_default(self):
        """User objects should have no permission by default."""
        self.assertEqual(len(self.member.permissions), 0)
        
    def test_getting_by_email(self):
        """Users should be fetcheable by their email addresses"""
        model.DBSession.add(self.member)
        him = model.User.by_email_address(u"ignucius@example.org")
        self.assertEqual(him, self.member)
