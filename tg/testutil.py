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
    
    def setUp(self):
        assert self.model != None, "Database test cases must define the model"
        assert self.database != None, "Database test cases must define the "\
                                      "database"
        self.model.init_model(self.database)
        self.model.metadata.create_all(self.database)
    
    def tearDown(self):
        self.model.DBSession.rollback()
        self.model.metadata.drop_all(self.database)
        