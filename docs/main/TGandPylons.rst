

TurboGears and Pylons Working Together
===============================================

:Status: Draft

.. contents:: Table of Contents
    :depth: 2



TurboGears 2 will be what TG has been designed to be from the beginning: a stack of best of breed
Python components.  We'll make sure these components are wired together to provide a web experience 
that gets you started quickly, and provides a robust web development environment.  TurboGears 2 
will also be as API compatible with TurboGears 1 as is reasonable. We do want to make a few API 
changes, and clean things up a bit as we go. But it should be very easy to port applications 
from TurboGears 1 to TurboGears 2.

The question has been asked, what does TurboGears 2 do to benefit Pylons development?  The simple
answer is that TurboGears 2 provides Pylons with a set of standard components, a new controller 
publishing API that is easier to get started with than Routes, a bunch of additional rapid web 
development tools, and perhaps most importantly a lot more developer attention.

By working together on core components, we'll be able to move forward more quickly, and put even 
more effort into creating a robust, stable core.    

Pylons provides a robust WSGI stack, and a clean way to re-implement the TurboGears API in 
relatively little code. And since Pylons has a goal of being a framework that maximizes developer
choices, people have been pushing Ben and the rest of the Pylons developers to make a well
documented set of defaults, and to make the framework a bit easier for new developers to learn.

In the new TurboGears+Pylons working together world, we're both able to focus on the things that
have made our individual frameworks successful in the past, and share development effort on lots
and lots of things.



