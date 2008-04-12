

Future Plans
------------

 * Widget browser
 * Tidy up: remove rule dispatch dependency, etc.
 * More interesting built-in widgets, e.g. growable forms, choice fields that show and hide options depending on selection
 * More hooks for doing custom validation, e.g. fields that become compulsory depending on the value of another field


With the current design, the widgets system needs to interact with the framework to:

 * Serve static resources
 * Detect what widgets are used on each page
 * Inject JS/CSS links into output page
 * Use request local storage

This goes beyond being WSGI middleware and requires tighter binding. The lxml approach has the potential to reduce binding considerably.
