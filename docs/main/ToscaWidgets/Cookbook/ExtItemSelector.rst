
ExtJS ItemSelector Widget
=========================


Installation
------------

::
  
  easy_install tw.extjs


Usage
-----

The ItemSelector widget aka SelectShuttle allows selection / deselection of multiple items from a select list. The ExtJS ItemSelector widget supports powerful features like drag and drop and ordering of selected items. The basic usage of this widget is demonstrated below. The widget uses the following parameters:

Parameters:
~~~~~~~~~~~~~~~~~~~~~
+-------------------------+---------------------------------------------+---------------------+
| **Name**                | **Description**                             | **Default**         |
+-------------------------+---------------------------------------------+---------------------+
| divID                   | The id of the element containing the widget.|                     |
+-------------------------+---------------------------------------------+---------------------+
| url                     | The url of the form action                  |                     |
+-------------------------+---------------------------------------------+---------------------+
| width                   | Width of the Form Panel container in px.    |'auto'               |
+-------------------------+---------------------------------------------+---------------------+
| fieldLabel              | Label for the ItemSelector Field.           | None                |
+-------------------------+---------------------------------------------+---------------------+
| labelWidth              | The width of the field label in pixels.     | 'auto'              |
+-------------------------+---------------------------------------------+---------------------+
| fromData                | A list of source selection items.           | []                  |
+-------------------------+---------------------------------------------+---------------------+
| toData                  | A list of destination selection items.      | [] (Each item in the|
|                         |                                             | fromData and toData |
|                         |                                             | lists is a data     |
|                         |                                             | record represented  |
|                         |                                             | as a list (typically|
|                         |                                             | containing a value  |
|                         |                                             | and a description)) |
+-------------------------+---------------------------------------------+---------------------+
| msWidth                 | The width of the MultiSelect field in px.   | 200                 |
+-------------------------+---------------------------------------------+---------------------+
| msHeight                | The height of the MultiSelect field in px.  | 300                 |
+-------------------------+---------------------------------------------+---------------------+
| dataFields              | A list of fields used for storing the data. | [0, 1]              |
+-------------------------+---------------------------------------------+---------------------+
| valueField              | Field for storing the values.               | 0                   |
+-------------------------+---------------------------------------------+---------------------+
| displayField            | Field that is displayed.                    | 1                   |
+-------------------------+---------------------------------------------+---------------------+
| fromLegend              | Legend for the source select Field.         | None                |
+-------------------------+---------------------------------------------+---------------------+
| toLegend                | Legend for the destination select Field.    | None                |
+-------------------------+---------------------------------------------+---------------------+
| submitText              | Text for the submit button.                 | 'Submit'            |
+-------------------------+---------------------------------------------+---------------------+
| resetText               | Text for the reset button.                  | 'Reset'             |
+-------------------------+---------------------------------------------+---------------------+



The widget can be instantiated as follows::

    from tw.extjs import ItemSelector

    from_data = [["AL","Alabama"], ["AK","Alaska"], ["AZ","Arizona"], ["AR","Arkansas"], ["CA","California"], .... ["WY","Wyoming"]]
    to_data = []

    item_selector = ItemSelector(divID='item_selector_div',
                             width=550,
                             url='/save',
                             fieldLabel='States',
                             labelWidth=40,
                             fromData=from_data,
                             toData=to_data,
                             msWidth=200,
                             msHeight=200,
                             dataFields=['code','desc'],
                             valueField='code',
                             displayField='desc',
                             fromLegend='Available',
                             toLegend='Selected',
                             submitText='Save',
                             resetText='Reset')

It can be then served up to the user via a controller method like this::
  
   @expose('mypackage.templates.myformtemplate')
   def index(self, **kw):
       pylons.c.field = item_selector
       return dict()

The widget can then be displayed in the template like this::

   ${tmpl_context.field()}

This brings up the ItemSelector on the browser. It allows shuttling of items between the source and destination Fields and ordering of items selected in the destination field using the arrow keys or by dragging and dropping the items at the correct place. This is how it looks in the browser:


 .. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/ExtItemSelector?action=AttachFile&do=get&target=itemselector1.png
       :alt: example ItemSelector
   :width: 500

