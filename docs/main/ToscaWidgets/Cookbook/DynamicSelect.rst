

How to create a database-driven select field
============================================

Most developers create database tables which allow select fields in their forms to be dynamically updated when a change occurs in the database.  The challenge is that widgets are stateless, and therefore select fields expect to have the same options from the time they are instantiated.  However, ToscaWidgets does allow widget parameters to change "on the fly"  Here is a description of one way a developer might update these parameters and allow dynamic select options.

Consider the following model snippet::

 from sqlalchemy import Table, Column, types
 from sqlalchemy.orm import mapper

 genera_table = Table("genera", metadata,
    Column("id", types.Integer, primary_key=True),
    Column("name", types.String(100), nullable=False),
    Column("description", types.Text, nullable=True),
    )

 class Genera(object):
    pass

 mapper(Genera, genera_table)

The trick here is to override the update_params mdethod of SingleSelectField to query the database for the records, and then add them to the 'options' parameter before processing the rest of the TW.

::
 
 from mypackage.model import Genera
 from tw.forms import SingleSelectField
 from tg2 import DBSession
 
 class MySelect(SingleSelectField):
    def update_params(self, d):
        rows = DBSession.query(Genera).fetchall()
        rows= [(row['id'], row['name']) for row in rows]
        d['options']= rows
        SingleSelectField.update_params(self, d)
        return d

A more intelligent solution would be to cache the rows and then refresh them every so often.

::
 
 from mypackage.model import Genera
 from tw.forms import SingleSelectField
 from tg2 import DBSession
 import time

 timestamp = time.time()
 options = []
 
 class MySelect(SingleSelectField):
    def update_params(self, d):
        global timestamp
        global options
   
        #refresh once a minute at the most:
        if time.time() - timestamp > 60:
            rows = DBSession.query(Genera).fetchall()
            options = [(row['id'], row['name']) for row in rows]
   
        d['options'] = options
        SingleSelectField.update_params(self, d)
        return d
