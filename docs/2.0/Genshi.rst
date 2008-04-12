Working with Genshi in your Views/Templates
============================================


TurboGears uses Genshi, a template language that is smart about markup, as the default template engine.

genshi syntax
--------------

to be filled...

Genshi gothcas
--------------

DO NOT USE 'data' as a key in the return dictionary of your controller. This can provide a somewhat confusing AttributeError on the Context object.   Currently the error message provides no mention of 'data' being a reserved word.

Using alternative template engines
-------------------------------------

to be filled...


Reference:

http://genshi.edgewall.org/


