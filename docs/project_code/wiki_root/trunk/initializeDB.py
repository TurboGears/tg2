from wiki20.model import DBSession, Page, metadata
from sqlalchemy import create_engine

# Prepare the database connection
engine = create_engine("sqlite:///devdata.db", echo=True)
DBSession.configure(bind=engine)

# Create the tables
metadata.drop_all(engine)
metadata.create_all(engine)

# Create a page object and set some data
page = Page("FrontPage", "initial data")

# Save the page object to the in memory DBSession
DBSession.save(page)

