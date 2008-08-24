

OpenLayers Map Widget
=====================


Introduction
------------

OpenLayers is a Javascript Toolkit for creating web mapping applications. Its is licensed under the liberal BSD license and is being used extensively on various mapping applications.

An Openlayers Map typically consists of a map object consisting of a viewport which is contained in a standard html DIV element. The map contains one or more Layer objects which are also html DIVs in their own right and render images based on data queried from one or more servers. The layer data is obtained using one of the several web mapping APIs that are commonly used on the Internet, like Google Maps API, Yahoo Maps API or the APIs based on the Open Geospatial Consortium (OGC) Specifications, e.g. Web Map Service (WMS), Web Feature Service (WFS), Geography Markup Language (GML), etc. Apart from the layers, a map would also have some map control objects like the LayerSwitcher (for arranging the oder of layers), PanZoomBar (for panning and zooming), etc.


About this Tutorial
-------------------

In this tutorial we would create an OpenLayers Map with several layers and controls using the ToscaWidgets library for OpenLayers, viz. tw.openlayers. 


Installation
------------

::
  
  easy_install tw.openlayers


Creating the Layers:
--------------------

First of all we create the layers required to be rendered in the map. The layers should be created as a WidgetsList, which is described as "syntactic sugar for declaring a list of widgets" by Alberto, the creator of ToscaWidgets. The following code shows creation of layers with 6 different layer objects. Three layers using data accessible through OGC WMS and one each using Google, Yahoo and MS VirtualEarth APIs. Note that the API Keys used below for Google and Yahoo must be replaced with suitable keys generated for the site hosting the map::

    from tw.api import WidgetsList, js_symbol
    from tw.openlayers import WMS, Google, Yahoo, VirtualEarth

    GOOGLE_API_KEY = 'ABQIAAAAPROe5rfmjTLGwsrGDo3yxhT2yXp_ZAY8_ufC3CFXhHIE1NvwkxS-_alF99xZR7Ix1DNJft1bfQlvaQ'
    YAHOO_API_KEY = 'mgJlSabV34HNd3cxUHD3Bdn5hcIolDi7oS4_U1Zs55ym9Gpv3499TaVwy8Q-'
    VE_API_KEY = ''

    class MyLayers(WidgetsList):
        ol = WMS(name="OpenLayers WMS",
                url=['http://labs.metacarta.com/wms/vmap0'],
                options={'layers': 'basic'})
        nasa = WMS(name="NASA Global Mosaic",
                url=['http://t1.hypercube.telascience.org/cgi-bin/landsat7'],
                options={'layers': 'landsat7'})
        dmdemo = WMS(name="DM Solutions Demo",
                url=['http://www2.dmsolutions.ca/cgi-bin/mswms_gmap'],
                options={'layers': 'bathymetry,land_fn,park,drain_fn,drainage,prov_bound,fedlimit,rail,road,popplace',
                      'transparent': True,
                      'opacity': 0.4,
                      'format': 'image/png'},
                display={'minResolution': 0.17578125,
                      'maxResolution': 0.703125})
        google = Google(name="Google Maps", apikey=GOOGLE_API_KEY,
            options=dict(type=js_symbol('G_HYBRID_MAP')))
        yahoo = Yahoo(name="Yahoo Maps", apikey=YAHOO_API_KEY)
        ve = VirtualEarth(name="VE", apikey=VE_API_KEY, isBaseLayer = True)


The WMS layers take a *url* parameter. This is a list of urls running the service. All the layers support an *options* and a *display* parameter. These parameters are required for passing additional layer options and display options. Checkout the OpenLayers API Docs for the various supported parameters.


Creating the Map Controls
-------------------------

Similar to the Layers, the map Controls are also created as a WidgetsList. They are initialized as follows::

    from tw.openlayers import LayerSwitcher, OverviewMap, PanZoomBar

    cass MyControls(WidgetsList):
        ls = LayerSwitcher()
        ovm = OverviewMap()
        ovm = Navigation()
        pzm = PanZoomBar()


Creating the Map
----------------

Finally the Map object is created using the layers and the controls created above and placed in the template context inside the controller method::

    from tw.openlayers import Map

    map = Map(id='map', layers=MyLayers(), controls=MyControls())

    class RootController(BaseController):

        @expose('samplemap.templates.index')
        def index(self):
            pylons.c.map = map
            return dict(page='index')

Calling the Map in the Template
-------------------------------

The map is rendered in the template by calling it from the template context::

   ${tmpl_context.map()}

The map can then be viewed in the browser. A screenshot is shown as example:

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/OpenLayersMap?action=AttachFile&do=get&target=openlayersmap.png
    :alt: example OpenLayers Map


