
Serving static files (CSS, JavaScript, images, etc)
=======================================================


Place static files in 'public' folder.  If no these files will be served up from there just as they would in a "normal" web server. You might want to consider putting all static files in a static directory, so that you can use apache/nginx to serve up these static files for you when you go into production, or later when you're traffic requires it. 


Getting rid of the static file middleware
-----------------------------------------

If your app is running in production, and Apache or another web server is handling this static content, edit config/middleware.py and remove ::

  javascripts_app = StaticJavascripts()
  static_app = StaticURLParser(config['pylons.paths']['static_files'])
  app = Cascade([static_app, javascripts_app, app])

Reference
-----------

 upload file
 
 * http://wiki.pylonshq.com/display/pylonscookbook/Hacking+Pylons+for+handling+large+file+upload
 * http://kelpi.com/script/06fff7




