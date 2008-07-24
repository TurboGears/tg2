

JQuery TreeView Widget
==========================


Installation
------------

::
  
  easy_install tw.jquery


Usage
-----

The TreeView widget supports the following optional parameters:

Parameters:
~~~~~~~~~~~
* **treeDiv** The id of the div element which contains the unordered list to be rendered as a tree. (*Default:* treeDiv = tree)

For example the widget is instantiated as::

    from tw.jquery import TreeView

    myTree = TreeView(treeDiv='navTree')

This tree is served up to the user via a controller method like this::
  
   @expose('mypackage.templates.navtree')
   def navtree(self, **kw):
       pylons.c.tree = myTree
       return dict()

And your template would display the tree like this::

   ${tmpl_context.tree()}

The template should have a div with id navTree containing an unordered list as::

    <div id="navTree">
      <ul>
        <li class="open">TurboGears2
          <ul>
             <li><a href="http://docs.turbogears.org/2.0">Documentation</a></li>
             <li><a href="http://docs.turbogears.org/2.0/API">API Reference</a></li>
             <li><a href="http://trac.turbogears.org/turbogears/">Bug Tracker</a></li>
             <li><a href="http://groups.google.com/group/turbogears">Mailing List</a></li>
          </ul>
         </li>
        <li class="closed">Pylons
          <ul>
             <li><a href="http://wiki.pylonshq.com/display/pylonsdocs/Home">Documentation</a></li>
             <li><a href="http://wiki.pylonshq.com/display/pylonsfaq/Home">FAQ</a></li>
             <li><a href="http://pylonshq.com/project/">Bug Tracker</a></li>
             <li><a href="http://groups.google.com/group/pylons-discuss">Mailing List</a></li>
          </ul>
         </li>
        <li class="closed">SQLAlchemy
          <ul>
             <li><a href="http://www.sqlalchemy.org/docs/">Documentation</a></li>
             <li><a href="http://www.sqlalchemy.org/trac/wiki/FAQ">FAQ</a></li>
             <li><a href="http://www.sqlalchemy.org/trac/query">Bug Tracker</a></li>
             <li><a href="http://groups.google.com/group/sqlalchemy">Mailing List</a></li>
          </ul>
         </li>
      </ul>
    </div>

Note that some items have class="closed". These would show up as collapsed nodes.

Here is the resulting field when viewed from a browser:

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/TreeView?action=AttachFile&do=get&target=treeview.png
    :alt: example TreeView
