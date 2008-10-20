from sqlalchemy import *
from sqlalchemy.orm import mapper
from wiki20.model import metadata

# Database table definition
# See: http://www.sqlalchemy.org/docs/04/sqlexpression.html

pages_table = Table("pages", metadata,
    Column("id", Integer, primary_key=True),
    Column("pagename", Text, unique=True),
    Column("data", Text)
)

# Python class definition
class Page(object):
    def __init__(self, pagename, data):
       self.pagename = pagename
       self.data = data

# Mapper
# See: http://www.sqlalchemy.org/docs/04/mappers.html
page_mapper = mapper(Page, pages_table)

