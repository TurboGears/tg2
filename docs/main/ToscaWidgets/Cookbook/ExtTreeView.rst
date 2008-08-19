
ExtJS Tree Widget
==================


Installation
------------

::

 easy_install tw.extjs


Usage
---------

Widget definition

::
  
 from tw.extjs import TreeView
 extTree = TreeView(divID='treeView1', fetch='fetchTree')


Server side
-----------
::

    @expose('myproject.templates.tableview')
    def ext(self):
        pylons.c.tree = extTree
        return dict()

Template code
--------------

::

 ${tmpl_context.tree()}


Fetch code
----------

::
    
    import simplejson
    def _getData(self, node):
        #return a list of dictionaries
        #dictionaries have the format:
        # {'text':visible_node_name, 'id':identifier, 'cls':'file'|'folder', 'allowChildren':False, 'leaf':True}      
        #return the data for a given node
        #more here soon
        pass


    @expose()
    def fetchTree(self, node):
        r = [self._getData(node),]
        return simplejson.dumps(r)

