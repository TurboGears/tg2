Working with Genshi in your Views/Templates
============================================


TurboGears uses Genshi, a template language that is smart about markup, as the default template engine.

Simple genshi example
--------------------------

Genshi is an XML template language based on Kid, which in turn was inspired by zope's TAL.  Genshi is the default template language of TurboGears2, and it provides a very similar API to it's predecessor.

Genshi Templates look like XHTML.  Here's a sample genshi template:

.. code-block:: html

    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" 
                          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml"
          xmlns:py="http://genshi.edgewall.org/"
          xmlns:xi="http://www.w3.org/2001/XInclude">
    
    <xi:include href="master.html" />
    
    <head>
      <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
      <title>Sample Template, for looking at template locals</title>
    </head>
    
    <body>
        <h1>All objects from locals():</h1>
    
        <div py:for="item in sorted(locals()['data'].keys())">
          ${item}: ${repr(locals()['data'][item])}</div>
    </body>
    </html>

This particular template does a couple of things, but it's main function is to take each variable that's been made available in the template namespace and display it's name and it's value. 

Every template language in the world needs to provide a variable substitution syntax, and the standard way in python seems to be ``${item}``, and that's exactly what you do in Genshi.  Take a variable wrap it in curly braces and throw a $ in front, and the value of the variable will be substituted in when the template is rendered.   Genshi is nice in that it allows you to use full python expressions in the substitution.  

So, in our above template when Genshi sees::

  ${repr(locals()['data'][item])}
  
it evaluates the python expression ``repr(locals()['data'][item])`` and provides the string representation of the proper item. 

And if you look a line up, you'll see where item is defined as one of the list of keys in the dictionary representing the local variables. The way this works is that py:for acts just like a standard python for loop, repeating the <div> that it's (and it's children if there were any) once for each item in the dictionary. 

In TurboGears 2 the template namespace is going to be populated with the items you return in your controller's return dictionary, along with a few extras.   This particular template can be very helpful when debugging a controller's return values, and is included in the default quickstarted project for you. 

The general way that Genshi works it that it allows you to add special attributes to your xml elements, called *Template Directives*.  Each of these template directives should be given a value, which can be ANY python expression.  So, learning Genshi is pretty much about leanring how those directives work, since the rest is just python.    And like py:for, most of the directives are very "python like". 

Available Processing Directives:
------------------------------------------

Here's a list of all the Template Directives in Genshi, along with a brief description. 

======================= ======================
Gensh Directive         Definition
======================= ======================
``py:if``               Displays the element and it's children if the condition is true.
``py:choose``           Used with py:when and py:otherwise to select one of several options to be rendered.
``py:when``             Used with py:choose -- displays an element and it's children when the condition is true.
``py:otherwise``        Used with py:when and py:choose, displays if non of the when clauses are true.
``py:for``              Repeats the element (and it's children) for each item in some iterable
``py:with``             Lets you assign expressions to variables
``py:replace``          Replaces the element with the contents of the expression, stripping out the element itself.
``py:def``              Creates a re-usable "template function" that can be used to render template 
                        snippets based on the arguments passed in. 
``py:match``            given an XPath expression, it finds and replaces every element in the 
                        template that matches the expression --  with the content of the element
                        containing the py:match.
``py:strip``            Removes just the containing element (not it's children) if the condition is true. 
======================= ======================


There are examples of how each of these template directives work on the Genshi web site.  

http://genshi.edgewall.org/wiki/Documentation/xml-templates.html

Genshi gotchas
------------------

DO NOT USE 'data' as a key in the return dictionary of your controller. This can provide a somewhat confusing AttributeError on the Context object.   Currently the error message provides no mention of 'data' being a reserved word.

Further Reading
-------------------

http://genshi.edgewall.org/wiki/Documentation/xml-templates.html


