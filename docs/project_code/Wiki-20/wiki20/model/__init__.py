"""The application's model objects"""

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import MetaData


# Global session manager.  DBSession() returns the session object
# appropriate for the current web request.
DBSession = scoped_session(sessionmaker(autoflush=True, transactional=True))

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database.
metadata = MetaData()

#####
# Generally you will not want to define your table's mappers, and data objects
# here in __init__ but will want to create modules them in the model directory
# and import them at the bottom of this file.  
#
######

def init_model(engine):
    """Call me before using any of the tables or classes in the model."""
    
    # If you are using reflection to introspect your database and create 
    # table objects for you, your tables must be defined and mapped inside 
    # the init_model function, so that the engine is available if you 
    # use the model outside tg2, you need to make sure this is called before
    # you use the model. 

    #
    # See the following example: 
    
    #global t_reflected
    
    #t_reflected = Table("Reflected", metadata,
    #    autoload=True, autoload_with=engine)

    #mapper(Reflected, t_reflected)

# Import your model modules here. 
##{ModelModules}
from wiki20.model.page import Page, pages_table
##
