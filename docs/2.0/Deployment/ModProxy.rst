


mod_proxy -- Running TG2 behind Apache
=======================================

:status: Draft

.. contents::
    :depth: 2


By running your TurboGears2 application behind Apache you can take 
advantage of Apache's HTTPS abilities or have it serve your static files.


Using Apache as a Reverse Proxy
-------------------------------


TurboGears configuration
~~~~~~~~~~~~~~~~~~~~~~~~

If you're mounting your TG2 app at the root of the website, there's nothing you need to do.   But if you're mounting it somewhere else, you need to edit production.ini to include these changes::

  [app:main]
  use = egg:your_project_name
  filter-with = proxy-prefix
  # Usual options here

  [filter:proxy-prefix]
  use = egg:PasteDeploy#prefix
  prefix = /wherever_your app_is mounted

basically this just tells paster where your app is going to be mounted so that it can manage the URL's for you properly. 

:Warning: You will also want to make sure that you disable the debugger middleware. 

Make sure you have this line in production.ini ::
	
   full_stack = False


Apache Configuration
~~~~~~~~~~~~~~~~~~~~

Here is how to configure Apache 2 as a reverse proxy for your TurboGears2 application.

In Apache's ``httpd.conf`` uncomment the ``mod_proxy`` modules::

    LoadModule proxy_module modules/mod_proxy.so
    LoadModule proxy_connect_module modules/mod_proxy_connect.so
    LoadModule proxy_http_module modules/mod_proxy_http.so
    LoadModule proxy_balancer_module modules/mod_proxy_balancer.so

Also note, depending on your distribution, you first might need to install the
``apache-mod_proxy`` packages.

In the virtual hosts section of the ``httpd.conf`` file or in the include file
for your virtual host (e.g. ``httpd-vhosts.conf``, but make sure this is loaded),
you would want to have something like this for your site (adapt the server name,
admin, log locations etc.)::

    NameVirtualHost *

    <VirtualHost *>
        ServerName mytgapp.blabla.com
        ServerAdmin here-your-name@blabla.com
        #DocumentRoot /srv/www/vhosts/mytgapp
        Errorlog /var/log/apache2/mytgapp-error_log
        Customlog /var/log/apache2/mytgapp-access_log common
        UseCanonicalName Off
        ServerSignature Off
        AddDefaultCharset utf-8
        ProxyPreserveHost On
        ProxyRequests Off
        ProxyPass /error/ !
        ProxyPass /icons/ !
        ProxyPass /favicon.ico !
        #ProxyPass /static/ !
        ProxyPass / http://127.0.0.1:8080/
        ProxyPassReverse / http://127.0.0.1:8080/
    </VirtualHost>

Uncomment the ``DocumentRoot`` and ``ProxyPass /static/`` lines if you want to serve the directory with static content of your TurboGears application directly by Apache. You will then also need to copy or link this directory to the configured ``DocumentRoot`` directory.

Check that your Apache configuration has no problems::

    apachectl -S

or::

    apachectl configtest

If everything is ok, run::

        apachectl start

Finally, go to your TurboGears project directory and in a console run::

        python start-myproject.py prod.cfg

Now you should be able to see your webpage in full TurboGears glory
at the address configured as ``ServerName`` above.

To be able to relocate your application without problems, make sure you
create your URLs properly (see `1.0/GettingStarted/URLs`_).


Setting the Correct Charset
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default Kid templates used by TurboGears specify ``utf-8`` as a charset.
The Apache default charset, returned in the ``Content-Type`` header, is ``ISO-8859-1``.
This inconsistency will cause errors during validation and incorrect rendering of
some characters on the client. Therefore we used the ``AddDefaultCharset utf-8`` directive
above to override the Apache default in the TurboGears virtual host section.

You can also explicitly set the charset property on a by-method basis by
sending the ``Content-type`` HTTP header from CherryPy. To do this, you woud
add the following line to your controller methods in ``controllers.py``,
somewhere before you return the data dictionary::

    cherrypy.response.headerMap["Content-Type"] += ";charset=utf-8"

Apache notices the pre-existing header and passes it through.
