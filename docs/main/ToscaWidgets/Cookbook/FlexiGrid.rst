

JQuery FlexiGrid Widget
==========================


Installation
------------

::
  
  easy_install tw.jquery


Usage
-----

The FlexiGrid widget supports the following parameters:

Mandatory Parameters:
~~~~~~~~~~~~~~~~~~~~~
* **id** The element id of the input field element. Multiple instanes of FlexiGrid can be used on the same page. These are referenced distinctly on the form page by the id.  This is also the element id of the flexigrid table and all jQuery operations reference the grid using this.
* **fetchURL** This is the url to be used for fetching the table data in JSON format using HTTP POST request.
* **colModel** This is a list of columns to be displayed in the grid. Each column is represented by a dictionary with the column name, display name, column width and alignment as the keys as shown below::

    colModel = [
                {'display':'ID', 'name':'id', 'width':20, 'align':'center'},
                {'display':'Title', 'name':'title', 'width':80, 'align':'left'},
                {'display':'Description', 'name':'description', 'width':100, 'align':'left'},
                {'display':'Year', 'name':'year', 'width':40, 'align':'center'},
                {'display':'Genera', 'name':'genera', 'width':40, 'align':'center'}
               ]


Optional Parameters:
~~~~~~~~~~~~~~~~~~~~
* **title** The table title.
* **sortname** The column on which rows are to be sorted
* **sortorder** The order of sort (*Default* : asc)
* **usepager** Whether pagination is to be used (*Default* : True)
* **useRp** Whether rows per page select box is displayed (*Default* : True)
* **rp** Rows per Page (*Default* : 25)
* **searchItems** List of columns to be displayed in the drop down list for searching matching records. This is a list of dictionaries containing the attribute name and the display name. This example shows a list of searchitems::

    searchItems = [
                {'display':'Title', 'name':'title', 'isdefault':True},
                {'display':'Year', 'name':'year'},
                {'display':'Genre', 'name':'genera'}
              ]

* **showTableToggleButton** The entire grid can be collapsed and expanded conveniently using this button (*Default* : False)
* **buttons** A list of buttons that should appear on the table header. Each button is provided as a dictionary. For example::

    buttons=[
      {'name':'Add', 'bclass':'add', 'onpress': 'add'},
      {'name':'Delete', 'bclass':'delete', 'onpress': 'delete'},
      {'separator':True}
    ]

The onpress key takes a javascript callback function as value which is called when the button is pressed. In this example, the Add button triggers the callback function add()

* **width** The width of the grid in px
* **height** The height of the grid in px

For example the widget could be instantiated as::

    from tw.jquery import FlexiGrid

    grid = FlexiGrid(id='flex', fetchURL='fetch', title='Movies',
                colModel=colModel, useRp=True, rp=10,
                sortname='title', sortorder='asc', usepager=True,
                searchItems=searchItems,
                showTableToggleButton=True,
                buttons=buttons,
                width=500,
                height=200
    )

Once the Widget is instantiated it can be served up to the user from the controller::

    @expose('samplegrid.templates.index')
    def index(self):
        pylons.c.grid = grid
        return dict()

The widget can be displayed in the template by::

   ${tmpl_context.grid(value=value)}

Before displaying the grid it is necessary to setup the controller method for serving the data using JSON as the data is fetched by the grid before it is rendered. The parameters passed to the FlexiGrid widget while instantiation are in turn passed to the controller method by the javascript code of the widget. The controller method for handling the JSON request would be::

    @validate(validators={"page":validators.Int(), "rp":validators.Int()})
    @expose('json')
    def fetch(self, page=1, rp=25, sortname='title', sortorder='asc', qtype=None, query=None):
        offset = (page-1) * rp
        if (query):
            d = {qtype:query}
            movies = DBSession.query(Movie).filter_by(**d)
        else:
            movies = DBSession.query(Movie)
        total = movies.count()
        column = getattr(Movie.c, sortname)
        movies = movies.order_by(getattr(column,sortorder)()).offset(offset).limit(rp)
        rows = [{'id'  : movie.id,
                     'cell': [movie.id, movie.title, movie.description, movie.year, movie.genera]} for movie in movies]
        return dict(page=page, total=total, rows=rows)

While all keyword parameters are the same as those passed to the widget during instantiation, the searchitems parameter is broken down by the flexigrid js module. The **qtype** parameter is a string value for the class attribute to be matched for searching and the **query** parameter contains the search string provided by the User. The above example provides equality match only.

Finally the FlexiGrid will be rendered as:

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/FlexiGrid?action=AttachFile&do=get&target=flexigrid.png
    :alt: example FlexiGrid Field
