"""
Place to hold TurboGears build-in templates

With quickstart command you can creates a new TurboGears 
project which you can use as a basis for your own project. 
The directory structure is as follows::
    
    - helloworld/
        - helloworld/
        - controllers.py
        - development.ini
        - setup.cfg
        - setup.py
        - test.ini

The setup.py file is used to create a re-distributable Python 
package of your project called an egg. Eggs can be thought of as 
similar to .jar files in Java. 
The setup.cfg file contains extra information about your project.

The helloworld directory within the helloworld directory is where all your 
application specific code and files are placed. 
The directory looks like this:: 

    - helloworld/
        - config/
        - controllers/
        - docs/
        - i18n/
        - lib/
        - models/
        - public/
        - __init__.py
        - websetup.py

The config directory contains the configuration options for your web application.

The controllers directory is where your application controllers are written. C
ontrollers are the core of your application where the decision is made on what 
data to load, and how to view it.

The docs directory is where you can write documentation for your project. 
You can then turn it into HTML using the command setup.py pudge.

The i18n directory is where your message catalogues are stored to support multiple languages.

The lib directory is where you can put code that is used between different 
controllers, third party code, or any other code that doesn't fit in well elsewhere.

The models directory is for your model objects, if you're using an ORM this is 
where the classes for them should go. 
Objects defined in models/__init__.py will be loaded and present as model.
YourObject inside your controllers. The database configuration string can be set 
in your development.ini file.

The public directory is where you put all your HTML, images, Javascript, CSS and 
other static files. It is similar to the htdocs directory in Apache.

The tests directory is where you can put controller and other tests. The controller 
testing functionality uses Nose and paste.fixture.

The templates directory is where templates are stored. Templates contain a mixture of 
plain text and Python code and are used for creating HTML and other documents in a way
that is easy for designers to tweak without them needing to see all the code that 
goes on behind the scenes. 
TurboGears 2 uses Genshi templates by default but also supports Mako, Cheetah, Kid and 
others through a system called Buffet. See how to change template languages.

The __init__.py file is present so that the helloworld directory can be used as a Python
module within the egg.

The websetup.py should contain any code that should be executed when an end user of your
application runs the paster setup-app command described in Application Setup. 
If you're looking for where to put that should be run before your application is, 
this is the place.

"""