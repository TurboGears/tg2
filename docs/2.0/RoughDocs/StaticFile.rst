

Serving static files (CSS and/or JavaScript)
============================================

:Status: Work in progres

.. contents:: Table of Contents
    :depth: 2

General case
-------------

Place static files in 'public' folder.


With web server
----------------

If your app is running in production, and Apache or another web server is handling this static content, edit config/middleware.py and remove ::

  javascripts_app = StaticJavascripts()
  static_app = StaticURLParser(config['pylons.paths']['static_files'])
  app = Cascade([static_app, javascripts_app, app])


Reference
-----------

 upload file
 
 * http://wiki.pylonshq.com/display/pylonscookbook/Hacking+Pylons+for+handling+large+file+upload
 * http://kelpi.com/script/06fff7




