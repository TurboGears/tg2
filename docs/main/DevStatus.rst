TurboGears 2 Project Status
===========================

TurboGears 2 arose out of some discussions about how similar the TurboGears 1 and Pylons frameworks were to each other.   We shared similar philosophies, and some similar implementation choices (we both used SQLObject and switched to SQLAlchemy for example).    

TurboGears is currently based on the as yet unreleased Pylons 0.9.7.  We plan to do a preview release of TG2 (version 1.9.7a1) shortly after the Pylons release.  We will will then track Pylons as they approach 1.0, with the intention of releasing TurboGears 2 at essentially the same time as Pylons 1.0. 

Current plans are to have the first official release 1.9.7a1 sometime early in April, and to have a full 2.0 release by the end of the year.   But open source projects are notoriously difficult to schedule, and it's possible that 2.0 will come out significantly before then, or that it will take longer.  

But we do plan on making 1.9.7 a stable release as soon as possible, which once it's out of beta should be production ready, if not feature complete. 

TG2 Core functionality
~~~~~~~~~~~~~~~~~~~~~~

TurboGears 2 is a fully functional implementation of the core TurboGears ideas:

 * Object Dispatch
 * expose and validation decorators
 * Full SQLAlchemy support
 * Buffet template support 
 * Controllers which return a dictionary
 * TG1 inspired helpers for Widgets and Form handling (based on ToscaWidgets)

So, porting to TG2 should be a relatively straightforward process.  TG 1.1 will provide a great stepping stone to TurboGears 2, it will include the same set of default components, use the same testing toolkit (WebTest), and will at the same time be very, very backwards compatible with 1.0.x. 

There is a major feature of TurboGears 1 which is not implemented in TurboGears
2: Automatic transaction support (this is likely to be replaced with a 
generalized transaction manager that handles multi-database transactions). 

General pre-release TurboGears 2 tasks:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 
 * Move all core documentation out of the Wiki and into Sphinx
 * Finish documenting TurboGears 2
 * Create a more complex tutorial than the 20 min wiki -- with complex database stuff. 
 * Improve test coverage 
