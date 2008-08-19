# -*- coding: utf-8 -*-
"""Utilities for unittesting TG2 projects"""

from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.orm import clear_mappers

__all__ = ['DBTest']


class DBTest(TestCase):
    """The base class for testing models in TG2 Projects."""
    model = None
    database = None
    
    def __init__(self, call_dad=True, *args, **kwargs):
        """Create a test case to test the model
        
        @param call_dad: The only way to test this class is by _not_
            calling unittest.TestCase.__init__() while running the test suite,
            and this parameter enable us to do so.
        @type call_dad: C{bool} 
        
        """
        if call_dad:
            super(DBTest, self).__init__(*args, **kwargs)
        assert self.model != None, "Database test cases must define the model"
        assert self.database != None, "Database test cases must define the "\
                                      "database"
    
    def setUp(self):
        self.model.metadata.create_all(self.database)
    
    def tearDown(self):
        self.model.metadata.drop_all(self.database)
        self.model.metadata.clear()
        try:
            self.model.metadata.dispose()
        except AttributeError: # not threadlocal
            if self.model.metadata.bind:
                self.model.metadata.bind.dispose()
        self.model._engine = None
