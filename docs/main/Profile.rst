
Profiling your app
==================

:Status: Work in progress

.. contents:: Table of Contents
    :depth: 2


TurboGears does not come with a built-in profiler, but an easy to use WSGI application profiler is just an easy_install away! 


Installing repoze.profile
---------------------------

First, install it with easy_install::

  easy_install -i http://dist.repoze.org/simple repoze.profile

Next add it to your WSGI stack in middleware.py::

  TODO: add code sample


Gathering profile data
---------------------------

Just fire up a browser (or functional test-runner like twill, ab (apache bench), or whatever).   The repoze.profile middleware will profile everything above it in the WSGI stack. 


Viewing profile data
---------------------------

There's a built in web based view of your profile data available....



Reference:

http://blog.repoze.org/repozeprofile-0_2-released.html


