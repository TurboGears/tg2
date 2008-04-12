


.. contents:: 
   :depth: 2

Adding JSON with MochiKit to the `TurboGears 2 Wiki Tutorial <http://docs.turbogears.org/2.0/Wiki20/All>`_
=========================================================================================================================

.. note :: This info is just copied over from the TG1 wiki tutorial, and needs to be vetted, expanded, and edited. 

This part of the tutorial is not technically AJAX. The "X" in AJAX stands for XML. I'm going to use `JSON`_ instead. JSON is easy and lightweight and efficient to use for all browsers. To use JSON for this TurboGears example, we just have to tell TurboGears that we want to use it via a second ``@expose()`` decorator.

.. _JSON: http://www.json.org/
.. parsed-literal::

    @expose("wiki20.templates.pagelist")
    **@expose("json")**
    def pagelist(self):
        pages = [page.pagename for page in Page.select(orderBy=Page.q.pagename)]
        return dict(pages=pages)


Now, if point your browser at http://localhost:8080/pagelist?tg_format=json, you'll see your pagelist in JSON format. Here's an example of how the JSON ouput looks like::

    {"tg_flash": null, "pages": ["FrontPage", "SandBox", "MyPage"]}

This easy conversion to JSON is the other use for returning a dictionary. In
standard CherryPy methods, you can return a string containing the rendered
page. You can do that with TurboGears as well, but a free JSON interface is a
pretty good reason to to it the TurboGears way. You can return as many formats
as you likeby stacking more ``@expose()`` decorators. Check out the `@expose
reference`_ article for details.

.. _@expose reference: 1.0/ExposeDecorator


from MochiKit import *
----------------------

For the client side of this tutorial, we'll be using MochiKit. 

To keep this from turning into a javascript tutorial (it's pretty long as-is
because we don't expect Pythonistas to be javascript masters), we're just going
to ajaxify one call by changing our "view complete page list" link to pull in
the pagelist and include it right in the page you're viewing.

The first thing we need to do is have MochiKit included in all of our pages. 
This can be done by editing the ``master.html`` file or by having TurboGears 
add it as a widget. 

The first thing you'll need to do is download and install the tw.mochikit 
package::

  easy_install tw.mochikit

TODO:  Add the toscawidget stuff here. 

Prep the page
-------------

Now that we have MochiKit, we're ready to modify our template. We'll practice good style by progressively enhancing our pagelist link in ``master.html``:

.. parsed-literal::

    <div id="footer">
    <p>View the <a **id="pagelist"** href="${tg.url('/pagelist')}">
        complete list of pages.</a>
    </p>
    **<div id="pagelist_results"></div>**
    <img src="/static/images/under_the_hood_blue.png" />

It doesn't look like much, but all we need is an ``id`` on our link and a place
to put the results. By doing it this way (instead of setting ``href="#"`` and
doing an ``onclick`` handler) we keep our page usable in all browsers, whether
they have JavaScript enabled or not.

The main event
--------------

In the interest of expediency (and because we're substituting URLs with gensh),
we'll add the handler to a ``<script>`` tag in the head rather than in its own
file.

.. parsed-literal::

        <style type="text/css" media="screen">
        @import "/static/css/style.css";
        </style>
        **<script type="text/javascript">**
        **addLoadEvent(function(){**
            **connect($('pagelist'),'onclick', function (e) {**
            **e.preventDefault();**
            **var d = loadJSONDoc("${std.url('/pagelist', tg_format='json')}");**
            **d.addCallback(showPageList);**
            **});**
        **});**
        **</script>**
        </head>

We're exercising a lot of MochiKit features here. The ``connect()`` function is
used to connect the ``onclick`` event of our pagelist link (MochiKit does a
getElementById if the first argument to connect is a string) to our anonymous handler
function. We could do the same thing by setting ``onclick`` directly on the
link itself, but this allows us to connect as many ``onclick`` handlers as we
like and makes maintenance simpler.

The handler function itself calls ``e.preventDefault()`` to prevent the click
from causing us to navigate away from the page and kicks off our replacement
behavior. A call to ``e.stop()`` would work just as well and would prevent
further `event propagation`_ from happening, ensuring that only the behavior
you specify for the event happens. For ``onclick`` replacements, your humble
tutorial writer prefers ``preventDefault`` in order to ensure that analytics
packages continue working.

.. _event propagation: http://www.quirksmode.org/js/events_order.html

MochiKit includes the ``loadJSONDoc`` function for doing an asynchronous
XMLHttpRequest and converting the result from JSON into a JavaScript object.
That's all there is to 'AJAX', really. Makes you wonder what all the fuss is
about. Notice we're using Kid substitution to ensure the url passed to
``loadJSONDoc`` is accurate, just like we would anywhere else.


Dealing with the consequences
-----------------------------

``loadJSONDoc`` returns a ``Deferred`` object. The idea with a ``Deferred`` is
that we know that our request for the pagelist will happen *some time in the
future*, but we don't know when. A ``Deferred`` is a placeholder that allows us
to specify what happens when the result comes in. We have a very simple
requirement here: call a function called ``showPageList``, which we'll write
now:

.. parsed-literal::

        <script type="text/javascript">
        addLoadEvent(function(){
            connect('pagelist','onclick', function (e) {
            e.preventDefault();
            var d = loadJSONDoc("${std.url('/pagelist', tg_format='json')}");
            d.addCallback(showPageList);
            });
        });
        **function showPageList(result) {**
            **var currentpagelist = UL(null, map(row_display, result["pages"]));**
            **replaceChildNodes("pagelist_results", currentpagelist);**
        **}**
        </script>

When ``loadJSONDoc`` gets its result, it will pass it along to
``showPageList``. The nice thing about this process is that ``result`` is the
same dictionary our ``pagelist`` method returned in Python! Even though we have
our list, we still need to convert it to HTML and insert it into the page. In
most javascript frameworks, you'd do this by concatinating HTML snippets or DOM
nodes, but MochiKit provides a better way.

The first line of ``showPageList`` shows off MochiKit.DOM, which provides a
conventiently named set of functions for creating common HTML elements. The
``UL()`` function is creating a new ``<UL>`` element with no attributes
(indicated by the ``null`` in the first argument). The second argument is for
the element's children, which we expect to be ``<LI>`` elements but instead
find this strange ``map()`` beast. The results are dumped into the
``pagelist_results`` element using ``replaceChildNodes()``.

As for that second argument, ``map()`` works exactly like it does in Python.
The function ``row_display`` (which we'll write next) is called for every item
in ``result["pages"]``.

If you're not used to functional programming this can be somewhat mind bending,
but it's basically a short way to write a for loop. Here's what ``map()`` looks
like (the actual implementation is more complex because it's more robust):: 

    // ILLUSTRATION ONLY, NOT PART OF THE TUTORIAL
    function map(func, list){
        var toReturn = [];
        for(var i = 0; i < list.length; i++){
            toReturn.push(func(list[i]));
        }
        return toReturn;
    }

As mentioned, we need a ``row_display`` function which will turn a WikiWord
title into a ``<LI>`` element containing a link to the corresponding page.

.. parsed-literal::

        function showPageList(result) {
            var currentpagelist = UL(null, map(row_display, result["pages"]));
            replaceChildNodes("pagelist_results", currentpagelist);
        }
        **function row_display(pagename) {**
            **return LI(null, A({"href" : "${std.url('/')}" + pagename}, pagename))**
        **}**
        </script>

The ``row_display()`` function further demonstrates MochiKit.DOM. Notice that
we're actually setting the ``href`` attribute for the ``<A>`` element. The
``std.url()`` is another instance of Kid substitution sneaking in. It's
replaced before any Javascript is run. The contents of the ``<A>`` itself are
the page name. MochiKit is smart and does the right thing here by inserting the
``pagename`` string as text content.

Whew! that was a lot of explanation for 6 lines of code. This
parent/map(formatter_function, children) pattern is very common when working
with MochiKit.DOM. You'll see a similar example in the official MochiKit
documentation.


Sweet success
--------------

Voila! If you go to your `front page`_ and click on the page list link, you'll
see the page list right there in the page.

.. _front page: http://localhost:8080/
