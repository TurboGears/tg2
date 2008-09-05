# -*- coding: utf-8 -*-
"""Utilities for unittesting TG2 projects"""

from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.orm import clear_mappers

from tg import config

__all__ = ['DBTest']


class DBTest(TestCase):
    """The base class for testing models in TG2 Projects.
    
    You should at least define C{model}. If you don't define C{database}, we'll
    create an SQLAlchemy engine with the DB URI defined in test.ini.
    
    """
    model = None
    database = None
    
    def setUp(self):
        assert self.model != None, "Database test cases must define the model"
        if self.database is None:
            self.database = config['pylons.app_globals'].sa_engine
        self.model.init_model(self.database)
        self.model.metadata.create_all(self.database)
    
    def tearDown(self):
        self.model.DBSession.rollback()
        self.model.metadata.drop_all(self.database)
        