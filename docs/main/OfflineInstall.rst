:status: Unofficial

An offline install of TG2 is not yet officially documented and supported, 
but the basic outline is to get all of the eggs you need and do easy_install 
using that local directory of eggs. 

You should be able to get the required eggs by doing an svn checkout of the 
egg files that go in the current online index:: 

  svn co http://svn.turbogears.org/site_resources/tg2_index/current/ eggs

Then once you've got the eggs you can  do: 

  $ cd eggs
  $ easy_install tg.devtools

To get the latest versions from SVN and install offline you can do a a SVN 
checkout of the TG2 sources, and a mercurial checkout of Pylons, and install 
those on top of the above eggs. 




