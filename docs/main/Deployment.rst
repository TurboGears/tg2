Deployment options
====================

TurboGears 2 provides a solid HTTP server built in, and for many internal corporate deployments or low traffic sites can you can just fire up the TG2 app and point people at it.

This can be as simple as running:: 

  paster serve production.ini

But it's also likely that you may want to automatically restart your TG2 app if the server reboots, or you may want to set it up as a windows service. Unfortunately these thing can be very operating system specific, but fortunately they aren't TG2 specific. 


Apache Deployment options:
---------------------------

* `mod_wsgi and virtualenv <Deployment/modwsgi%2Bvirtualenv>`_ -- the 
  mod_wsgi apache extension is a very efficient WSGI server, which provides 
  automatic process monitoring, load balancing for multi-process deployments,  
  as well as strong apache integration. 

* `Deploying with ModProxy <Deployment/ModProxy>`_ -- The mod_proxy 
  extension provides a simple to set-up apache environment that proxies 
  http requests to your tg2 app.   It can be used to load balance across 
  multiple machines.
 
* modRewrite -- mod_rewrite deployment is very similar to mod_proxy
  in fact from the TG2 side they are identical, but mod_rewrite can 
  be somewhat more complex to setup itself. 

NGINX deployment
-----------------

Nginx is a very fast asynchronous web server that can be used in front of 
TurboGears 2 in very high load environments. 

* load balancing proxy
* NGNX modWSGI

Packaging your app as an egg:
------------------------------

You may also want to package your app up as a redistributable egg, TG2 sets up everything that you need to do this. 

 * http://docs.turbogears.org/1.0/DeployWithAnEgg

Reference
-----------


You can also find recipes for mounting a Turbogears app behind lots of other servers in the 1.0 docs.  Generally these should "just work" with TG2 as well.   The only exception is that the config file production.ini is slightly different. 

 * http://docs.turbogears.org/1.0/Deployment


