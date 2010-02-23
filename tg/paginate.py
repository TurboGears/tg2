from webhelpers.paginate import Page as WhPage
from webhelpers.html import HTML
from tg import request

class Page(WhPage):

    def _pagerlink(self, pagenr, text):
        """
        Create a URL that links to another page using url_for().

        Parameters:

        pagenr
            Number of the page that the link points to

        text
            Text to be printed in the A-HREF tag
        """
        # Let the url_for() from webhelpers create a new link and set
        # the variable called 'page_param'. Example:
        # You are in '/foo/bar' (controller='foo', action='bar')
        # and you want to add a parameter 'pagenr'. Then you
        # call the navigator method with page_param='pagenr' and
        # the url_for() call will create a link '/foo/bar?pagenr=...'
        # with the respective page number added.
        link_params = {}
        # Use the instance kwargs from Page.__init__ as URL parameters
        link_params.update(self.kwargs)
        # Add keyword arguments from pager() to the link as parameters
        link_params.update(self.pager_kwargs)
        link_params[self.page_param] = pagenr

        # Create the URL to load a certain page
        link_url = link_params.get('link', request.path_info)
        link_url = '%s?page=%s'%(link_url, pagenr)
        # Create the URL to load the page area part of a certain page (AJAX updates)
        #link_params[self.partial_param] = 1
        partial_url = link_params.get('partial', '') #url_for(**link_params)

        if self.onclick: # create link with onclick action for AJAX
            try: # if '%s' is used in the 'onclick' parameter (backwards compatibility)
                onclick_action = self.onclick % (partial_url,)
            except TypeError:
                onclick_action = Template(self.onclick).safe_substitute({
                  "partial_url": partial_url,
                  "page": pagenr
                })
            return HTML.a(text, href=link_url, onclick=onclick_action, **self.link_attr)
        else: # return static link
            return HTML.a(text, href=link_url, **self.link_attr)
