.. _webhelpers:

==========
WebHelpers
==========

WebHelpers is a package designed to ease common tasks developers need that
are usually done for formatting or displaying data in templates.

Helpers available by module:


.. module:: webhelpers.date

Date
====

.. autofunction:: distance_of_time_in_words
.. autofunction:: time_ago_in_words


.. module:: webhelpers.feedgenerator

FeedGenerator
=============

The feed generator is intended for use in controllers, and generates an
output stream. Currently the following feeds can be created by imported the
appropriate class:

* RssFeed
* RssUserland091Feed
* Rss201rev2Feed
* Atom1Feed

All of these format specific Feed generators inherit from the 
:meth:`~webhelpers.feedgenerator.SyndicationFeed` class.

Example controller method::
    
    import logging

    from pylons import request, response, session
    from pylons import tmpl_context as c
    from pylons.controllers.util import abort, redirect_to, url_for
    from webhelpers.feedgenerator import Atom1Feed

    from helloworld.lib.base import BaseController, render

    log = logging.getLogger(__name__)

    class CommentsController(BaseController):

        def index(self):
            feed = Atom1Feed(
                title=u"An excellent Sample Feed",
                link=url_for(),
                description=u"A sample feed, showing how to make and add entries",
                language=u"en",
            )
            feed.add_item(title="Sample post", 
                          link=u"http://hellosite.com/posts/sample", 
                          description="Testing.")
            response.content_type = 'application/atom+xml'
            return feed.writeString('utf-8')

.. autoclass:: SyndicationFeed
    :members:
    
    .. automethod:: __init__
    

.. module:: webhelpers.html.converters

Converters
==========

Functions that convert from text markup languages to HTML

.. autofunction:: markdown
.. autofunction:: textilize


Secure Forms
============

.. automodule:: webhelpers.html.secure_form

.. autofunction:: secure_form


Tags
====

.. automodule:: webhelpers.html.tags

Form Tags
---------

.. autofunction:: checkbox
.. autofunction:: end_form
.. autofunction:: file
.. autofunction:: form
.. autofunction:: hidden
.. autofunction:: password
.. autofunction:: radio
.. autofunction:: select
.. autofunction:: submit
.. autofunction:: text
.. autofunction:: textarea
.. autoclass:: ModelTags
    :members:
    
    .. automethod:: __init__

Hyperlinks
----------

.. autofunction:: link_to
.. autofunction:: link_to_if
.. autofunction:: link_to_unless

Other Tags
----------

.. autofunction:: image

Head Tags
---------

.. autofunction:: auto_discovery_link
.. autofunction:: javascript_link
.. autofunction:: stylesheet_link

Utility
-------

.. autofunction:: convert_boolean_attrs


.. module:: webhelpers.html.tools

Tools
=====

Powerful HTML helpers that produce more than just simple tags.

.. autofunction:: auto_link
.. autofunction:: button_to
.. autofunction:: highlight
.. autofunction:: mail_to
.. autofunction:: strip_links


.. module:: webhelpers.mimehelper

MIMEType Helper
===============

The MIMEType helper assists in delivering appropriate content types for a
single action in a controller, based on several requirements:

1) Does the URL end in a specific extension? (.html, .xml, etc.)
2) Can the client accept HTML?
3) What Accept headers did the client send?

If the URL ends in an extension, the mime-type associated with that is given
the highest preference. Since some browsers fail to properly set their Accept
headers to indicate they should be serving HTML, the next check looks to see
if its at least in the list. This way those browsers will still get the HTML
they are expecting.

Finally, if the client didn't include an extension, and doesn't have HTML in
the list of Accept headers, than the desired mime-type is returned if the
server can send it.

.. autoclass:: MIMETypes
    :members:


.. module:: webhelpers.number

Number
======

Number formatting and calculation helpers.

.. autofunction:: format_number
.. autofunction:: mean
.. autofunction:: median
.. autofunction:: percent_of
.. autofunction:: standard_deviation
.. autoclass:: Stats
.. autoclass:: SimpleStats


Misc
====

.. automodule:: webhelpers.misc

.. autofunction:: all
.. autofunction:: any
.. autofunction:: no
.. autofunction:: count_true
.. autofunction:: convert_or_none


.. module:: webhelpers.pylonslib

Pylons-specific
===============

.. autoclass:: Flash
    :members:
    
    .. automethod:: __init__
    .. automethod:: __call__


Text
====

.. automodule:: webhelpers.text

.. autofunction:: chop_at
.. autofunction:: excerpt
.. autofunction:: lchop
.. autofunction:: plural
.. autofunction:: rchop
.. autofunction:: strip_leading_whitespace
.. autofunction:: truncate
.. autofunction:: wrap_paragraphs
