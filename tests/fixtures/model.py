"""A fake application's model objects"""

from datetime import datetime

from zope.sqlalchemy import ZopeTransactionExtension
from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.orm import scoped_session, sessionmaker, relation, backref, \
                           synonym
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String, Unicode, UnicodeText, Integer, DateTime, \
                             Boolean, Float


# Global session manager.  DBSession() returns the session object
# appropriate for the current web request.
maker = sessionmaker(autoflush=True, autocommit=False,
                     extension=ZopeTransactionExtension())
DBSession = scoped_session(maker)

# By default, the data model is defined with SQLAlchemy's declarative
# extension, but if you need more control, you can switch to the traditional
# method.
DeclarativeBase = declarative_base()

# Global metadata.
# The default metadata is the one from the declarative base.
metadata = DeclarativeBase.metadata

def init_model(engine):
    """Call me before using any of the tables or classes in the model."""
    DBSession.configure(bind=engine)


class Group(DeclarativeBase):
    """An ultra-simple group definition.
    """
    __tablename__ = 'tg_group'
    
    group_id = Column(Integer, autoincrement=True, primary_key=True)
    
    group_name = Column(Unicode(16), unique=True)
    
    display_name = Column(Unicode(255))
    
    created = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return '<Group: name=%s>' % self.group_name
