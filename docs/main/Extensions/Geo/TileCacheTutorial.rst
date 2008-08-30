

tg.ext.geo TileCache Tutorial
=============================


Introduction
------------

TileCache is a python WSGI (Web Services Gateway Interface) App that implements the WMS-C (Web Map Service - Cached) spec for generation and serving of WMS tiles. This improves the performance of a WMS service substantially by generating / querying tiles and locally caching them to serve subsequent tile requests. tg.ext.geo includes paster commands for creating controller code that mounts TileCache as a WSGI App.


About this Tutorial
-------------------

In this tutorial we would create a TG2 app and use tg.ext.geo extension to mount the TileCache WSGI App. We would also modify the template code for *index* method to create an OpenLayers Map that would render the tiles.


Installation
------------

It is assumed that a fresh virtualenv has been created and TG2 installed following the `TG2 Installation Guide <http://turbogears.org/2.0/docs/main/DownloadInstall.html#install-turbogears-2>`_. Install tg.ext.geo using easy_install::

    (tg2env)$ $ easy_install -i http://www.turbogears.org/2.0/downloads/current/index tg.ext.geo


Creating a New TG2 App
----------------------

Create a new TG2 app using the paster command and change into the newly created project folder::

    (tg2env)$ paster quickstart TilesApp
    (tg2env)$ cd TilesApp


Add tg.ext.geo Paster Plugin
----------------------------

Open the paster plugins file viz. TilesApp.egg-info/paster_plugins.txt and add a line containing *tg.ext.geo* . 


Create a TileCache Config
-------------------------

Create a TileCache config in the file tilecache.cfg in the project folder and add the necessary configuration. Details of this configuration can be found in the `TileCache Documentation <http://tilecache.org/readme.html#configuration>`_. A sample tilecache.cfg file can be downloaded from http://svn.tilecache.org/trunk/tilecache/tilecache.cfg . For example, a standard WMS tile service would have the following config::

    [cache]
    type=Disk
    base=/tmp/tilecache

    # Rendering VMAP0 data with WMS
    [basic]
    type=WMS
    url=http://labs.metacarta.com/wms/vmap0
    extension=png

Sections for all the required tilecache layers should be added to this file. For example, the following lines should be added in order to have a Mapnik Tiles layer using the OpenStreetMap (OSM) data::

    # Rendering OpenStreetMap data with Mapnik
    [osm]
    type=Mapnik
    mapfile=/home/user/osm-mapnik/osm.xml
    spherical_mercator=true

Mapnik is a C++ toolkit with python bindings for rendering maps. OpenStreetMap is a free geographic data set containing streetmaps. A document describing the rendering of OSM maps using Mapnik can be found `here <http://wiki.openstreetmap.org/index.php/Mapnik>_`.


Creating the Tiles Controller
-----------------------------

Once the tilecache.cfg file is ready, the new controller containing TileCache WSGI App can be created using the following paster command::

    (tg2env)$ paster geo-tilecache tiles

where tiles is the new controller. Now edit the root controller (package/controllers/root.py) to import and mount the controller::


    from tilesapp.controllers.tiles import TilesController

    class RootController(BaseController):
        tiles = TilesController()

The tiles controller should now be accessible at the url location `http://<host>:<port>/tiles`.

Start the server and point your browser to the above url. You should be able to see the TileCache Capabilities document, which an xml document describing the service.


Rendering the Tiles in an OpenLayers Map
----------------------------------------


Adding the Javascript Code
~~~~~~~~~~~~~~~~~~~~~~~~~~

The tiles accessible through the TileCache definition above can be rendered in an OpenLayers Map as a WMS or TMS layer depending upon the layer type defined in tilecache config. For a WMS layer modify the index template to add the following javascript code in the head section::

    <script src="/javascript/OpenLayers.js"></script>
    <script type="text/javascript">
        var map, layer;
        function init(){
            map = new OpenLayers.Map( $('map'), {'maxResolution': 360/512});
            layer = new OpenLayers.Layer.WMS( "VMap0", 
                    "http://localhost:8080/tiles", {layers: 'basic', format: 'image/png' } );
            map.addLayer(layer);
            if (!map.getCenter()) map.zoomToMaxExtent();
        }
    </script>

For a TMS Layer (e.g. OSM tiles in Spherical Mercator Projection) add the following javascript code::

    <script src="/javascript/OpenLayers.js"></script>
    <script type="text/javascript">
        var map, layer;
        function init(){
         options = {controls:[
                new OpenLayers.Control.LayerSwitcher(),
                new OpenLayers.Control.PanZoomBar()
                ]};
         options = OpenLayers.Util.extend({
            maxExtent: new OpenLayers.Bounds(-20037508.34,
                -20037508.34,20037508.34,20037508.34),
            maxResolution: 156543.0339,
            units: "m",
            projection: "EPSG:900913",
            transitionEffect: "resize"
        }, options);

        map = new OpenLayers.Map('map', options);

        layer = new OpenLayers.Layer.TMS("osm", "http://localhost:8080/tiles/",
                {layername: "osm", type: "png"});
        map.addLayer(layer);
        map.setCenter(new OpenLayers.LonLat(2.3, 48.86).transform(
                new OpenLayers.Projection("EPSG:4326"),
                new OpenLayers.Projection("EPSG:900913")), 15);
    }
    </script>

Download OpenLayers javascript mapping toolkit from `www.openlayers.org <http://www.openlayers.org/>_` and unzip / untar the archive. Copy the OpenLayers.js file and the img folder in the archive to project/public/javascript folder.


Adding the Style Code
~~~~~~~~~~~~~~~~~~~~~

The following stylesheet code may be added to suite the map display::

    <style type="text/css">
        #map {
            width: 100%;
            height: 100%;
        }
    </style>


Add the HTML Code
~~~~~~~~~~~~~~~~~

The following HTML code should be sufficient to show the map::

    <body onload="init();">
      <div id="map"></div>
      <div class="clearingdiv" />
      <div class="notice"> Thank you for choosing TurboGears.
      </div>
    </body>

See TileCache in Action
-----------------------

Its time to see TileCache in action now. Run the paster command to start the local http server::

    (tg2env)$ paster serve --reload development.ini

Point your browser to http://localhost:8080 to view the map. The first time you see the map and zoom in the tile would be generated and rendered. In the subsequent requests the response is much faster as tiles cached earlier are served up.

