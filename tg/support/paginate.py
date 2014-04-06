import re, string
from tg import request
from tg.controllers.util import url

from markupsafe import Markup
from markupsafe import escape_silent as escape

try:
    import sqlalchemy
    import sqlalchemy.orm
    from sqlalchemy.orm.query import Query as SQLAQuery
except ImportError:  # pragma: no cover
    class SQLAQuery(object):
        pass

try:
    from ming.odm.odmsession import ODMCursor as MingCursor
except ImportError:  # pragma: no cover
    class MingCursor(object):
        pass

def _format_attrs(**attrs):
    strings = [' %s="%s"' % (attr, escape(value)) for attr, value in attrs.items() if value is not None]
    return Markup("".join(strings))

def _make_tag(template, text, **attrs):
    return Markup(template % (_format_attrs(**attrs), escape(text))) 

class _SQLAlchemyQueryWrapper(object):
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, range):
        return self.obj[range]

    def __len__(self):
        return self.obj.count()

class _MingQueryWrapper(object):
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, range):
        return self.obj.skip(range.start).limit(range.stop-range.start)

    def __len__(self):
        return self.obj.count()

def _wrap_collection(col):
    if isinstance(col, SQLAQuery):
        return _SQLAlchemyQueryWrapper(col)
    elif isinstance(col, MingCursor):
        return _MingQueryWrapper(col)
    return col

class Page(object):
    """
    TurboGears Pagination support for @paginate decorator.
    It is based on a striped down version of the WebHelpers pagination class
    This represents a page inside a collection of items
    """
    def __init__(self, collection, page=1, items_per_page=20):
        """
        Create a "Page" instance.

        Parameters:

        collection
            Sequence, can be a a list of items or an SQLAlchemy query.

        page
            The requested page number - starts with 1. Default: 1.

        items_per_page
            The maximal number of items to be displayed per page.
            Default: 20.
        """
        self.kwargs = {}
        self.collection = _wrap_collection(collection)

        # The self.page is the number of the current page.
        try:
            self.page = int(page)
        except (ValueError, TypeError):
            self.page = 1

        self.items_per_page = items_per_page
        self.item_count = len(self.collection)

        if not self.item_count:
            #Empty collection, just set everything at empty
            self.first_page = None
            self.page_count = 0
            self.last_page = None
            self.first_item = None
            self.last_item = None
            self.previous_page = None
            self.next_page = None
            self.items = []
        else:
            #Otherwise compute the actual pagination values
            self.first_page = 1
            self.page_count = ((self.item_count - 1) // self.items_per_page) + 1
            self.last_page = self.first_page + self.page_count - 1

            # Make sure that the requested page number is the range of valid pages
            if self.page > self.last_page:
                self.page = self.last_page
            elif self.page < self.first_page:
                self.page = self.first_page

            # Note: the number of items on this page can be less than
            #       items_per_page if the last page is not full
            self.first_item = (self.page - 1) * items_per_page + 1
            self.last_item = min(self.first_item + items_per_page - 1, self.item_count)

            try:
                first = self.first_item - 1
                last = self.last_item
                self.items = list(self.collection[first:last])
            except TypeError: #pragma: no cover
                raise

            # Links to previous and next page
            if self.page > self.first_page:
                self.previous_page = self.page-1
            else:
                self.previous_page = None

            if self.page < self.last_page:
                self.next_page = self.page+1
            else:
                self.next_page = None

    def pager(self, format='~2~', page_param='page', partial_param='partial',
              show_if_single_page=False, separator=' ', onclick=None,
              symbol_first='<<', symbol_last='>>',
              symbol_previous='<', symbol_next='>',
              link_attr={'class':'pager_link'},
              curpage_attr={'class':'pager_curpage'},
              dotdot_attr={'class':'pager_dotdot'},
              page_link_template='<a%s>%s</a>',
              page_plain_template='<span%s>%s</span>',
              **kwargs):
        """
        Return string with links to other pages (e.g. "1 2 [3] 4 5 6 7").

        format:
            Format string that defines how the pager is rendered. The string
            can contain the following $-tokens that are substituted by the
            string.Template module:

            - $first_page: number of first reachable page
            - $last_page: number of last reachable page
            - $page: number of currently selected page
            - $page_count: number of reachable pages
            - $items_per_page: maximal number of items per page
            - $first_item: index of first item on the current page
            - $last_item: index of last item on the current page
            - $item_count: total number of items
            - $link_first: link to first page (unless this is first page)
            - $link_last: link to last page (unless this is last page)
            - $link_previous: link to previous page (unless this is first page)
            - $link_next: link to next page (unless this is last page)

            To render a range of pages the token '~3~' can be used. The
            number sets the radius of pages around the current page.
            Example for a range with radius 3:

            '1 .. 5 6 7 [8] 9 10 11 .. 500'

            Default: '~2~'

        symbol_first
            String to be displayed as the text for the %(link_first)s
            link above.

            Default: '<<'

        symbol_last
            String to be displayed as the text for the %(link_last)s
            link above.

            Default: '>>'

        symbol_previous
            String to be displayed as the text for the %(link_previous)s
            link above.

            Default: '<'

        symbol_next
            String to be displayed as the text for the %(link_next)s
            link above.

            Default: '>'

        separator:
            String that is used to separate page links/numbers in the
            above range of pages.

            Default: ' '

        page_param:
            The name of the parameter that will carry the number of the
            page the user just clicked on.

        partial_param:
            When using AJAX/AJAH to do partial updates of the page area the
            application has to know whether a partial update (only the
            area to be replaced) or a full update (reloading the whole
            page) is required. So this parameter is the name of the URL
            parameter that gets set to 1 if the 'onclick' parameter is
            used. So if the user requests a new page through a Javascript
            action (onclick) then this parameter gets set and the application
            is supposed to return a partial content. And without
            Javascript this parameter is not set. The application thus has
            to check for the existence of this parameter to determine
            whether only a partial or a full page needs to be returned.
            See also the examples in this modules docstring.

            Default: 'partial'

            Note: If you set this argument and are using a URL generator
            callback, the callback must accept this name as an argument instead
            of 'partial'.

        show_if_single_page:
            if True the navigator will be shown even if there is only
            one page

            Default: False

        link_attr (optional)
            A dictionary of attributes that get added to A-HREF links
            pointing to other pages. Can be used to define a CSS style
            or class to customize the look of links.

            Example: { 'style':'border: 1px solid green' }

            Default: { 'class':'pager_link' }

        curpage_attr (optional)
            A dictionary of attributes that get added to the current
            page number in the pager (which is obviously not a link).
            If this dictionary is not empty then the elements
            will be wrapped in a SPAN tag with the given attributes.

            Example: { 'style':'border: 3px solid blue' }

            Default: { 'class':'pager_curpage' }

        dotdot_attr (optional)
            A dictionary of attributes that get added to the '..' string
            in the pager (which is obviously not a link). If this
            dictionary is not empty then the elements will be wrapped in
            a SPAN tag with the given attributes.

            Example: { 'style':'color: #808080' }

            Default: { 'class':'pager_dotdot' }

        page_link_template (optional)
            A string with the template used to render page links

            Default: '<a%s>%s</a>'

        page_plain_template (optional)
            A string with the template used to render current page,
            and dots in pagination.

            Default: '<span%s>%s</span>'

        onclick (optional)
            This paramter is a string containing optional Javascript code
            that will be used as the 'onclick' action of each pager link.
            It can be used to enhance your pager with AJAX actions loading another
            page into a DOM object.

            In this string the variable '$partial_url' will be replaced by
            the URL linking to the desired page with an added 'partial=1'
            parameter (or whatever you set 'partial_param' to).
            In addition the '$page' variable gets replaced by the
            respective page number.

            Note that the URL to the destination page contains a 'partial_param'
            parameter so that you can distinguish between AJAX requests (just
            refreshing the paginated area of your page) and full requests (loading
            the whole new page).

            [Backward compatibility: you can use '%s' instead of '$partial_url']

            jQuery example:
                "$('#my-page-area').load('$partial_url'); return false;"

            Yahoo UI example:
                "YAHOO.util.Connect.asyncRequest('GET','$partial_url',{
                    success:function(o){YAHOO.util.Dom.get('#my-page-area').innerHTML=o.responseText;}
                    },null); return false;"

            scriptaculous example:
                "new Ajax.Updater('#my-page-area', '$partial_url',
                    {asynchronous:true, evalScripts:true}); return false;"

            ExtJS example:
                "Ext.get('#my-page-area').load({url:'$partial_url'}); return false;"

            Custom example:
                "my_load_page($page)"

        Additional keyword arguments are used as arguments in the links.
        """
        self.curpage_attr = curpage_attr
        self.separator = separator
        self.pager_kwargs = kwargs
        self.page_param = page_param
        self.partial_param = partial_param
        self.onclick = onclick
        self.link_attr = link_attr
        self.dotdot_attr = dotdot_attr
        self.page_link_template = page_link_template
        self.page_plain_template = page_plain_template

        # Don't show navigator if there is no more than one page
        if self.page_count == 0 or (self.page_count == 1 and not show_if_single_page):
            return ''

        # Replace ~...~ in token format by range of pages
        result = re.sub(r'~(\d+)~', self._range, format)

        # Interpolate '%' variables
        result = string.Template(result).safe_substitute({
            'first_page': self.first_page,
            'last_page': self.last_page,
            'page': self.page,
            'page_count': self.page_count,
            'items_per_page': self.items_per_page,
            'first_item': self.first_item,
            'last_item': self.last_item,
            'item_count': self.item_count,
            'link_first': self.page>self.first_page and\
                          self._pagerlink(self.first_page, symbol_first) or '',
            'link_last': self.page<self.last_page and\
                         self._pagerlink(self.last_page, symbol_last) or '',
            'link_previous': self.previous_page and\
                             self._pagerlink(self.previous_page, symbol_previous) or '',
            'link_next': self.next_page and\
                         self._pagerlink(self.next_page, symbol_next) or ''
        })

        return Markup(result)

    #### Private methods ####
    def _range(self, regexp_match):
        """
        Return range of linked pages (e.g. '1 2 [3] 4 5 6 7 8').

        Arguments:

        regexp_match
            A "re" (regular expressions) match object containing the
            radius of linked pages around the current page in
            regexp_match.group(1) as a string

        This function is supposed to be called as a callable in
        re.sub.

        """
        radius = int(regexp_match.group(1))

        # Compute the first and last page number within the radius
        # e.g. '1 .. 5 6 [7] 8 9 .. 12'
        # -> leftmost_page  = 5
        # -> rightmost_page = 9
        leftmost_page = max(self.first_page, (self.page-radius))
        rightmost_page = min(self.last_page, (self.page+radius))

        nav_items = []

        # Create a link to the first page (unless we are on the first page
        # or there would be no need to insert '..' spacers)
        if self.page != self.first_page and self.first_page < leftmost_page:
            nav_items.append( self._pagerlink(self.first_page, self.first_page) )

        # Insert dots if there are pages between the first page
        # and the currently displayed page range
        if leftmost_page - self.first_page > 1:
            # Wrap in a SPAN tag if nolink_attr is set
            text = '..'
            if self.dotdot_attr:
                text = _make_tag(self.page_plain_template, text, **self.dotdot_attr)
            nav_items.append(text)

        for thispage in range(leftmost_page, rightmost_page+1):
            # Hilight the current page number and do not use a link
            if thispage == self.page:
                text = '%s' % (thispage,)
                # Wrap in a SPAN tag if nolink_attr is set
                if self.curpage_attr:
                    text = _make_tag(self.page_plain_template, text, **self.curpage_attr)
                nav_items.append(text)
            # Otherwise create just a link to that page
            else:
                text = '%s' % (thispage,)
                nav_items.append( self._pagerlink(thispage, text) )

        # Insert dots if there are pages between the displayed
        # page numbers and the end of the page range
        if self.last_page - rightmost_page > 1:
            text = '..'
            # Wrap in a SPAN tag if nolink_attr is set
            if self.dotdot_attr:
                text = _make_tag(self.page_plain_template, text, **self.dotdot_attr)
            nav_items.append(text)

        # Create a link to the very last page (unless we are on the last
        # page or there would be no need to insert '..' spacers)
        if self.page != self.last_page and rightmost_page < self.last_page:
            nav_items.append( self._pagerlink(self.last_page, self.last_page) )

        return self.separator.join(nav_items)

    def _pagerlink(self, pagenr, text):
        """
        Create a URL that links to another page.

        Parameters:

        pagenr
            Number of the page that the link points to

        text
            Text to be printed in the A-HREF tag
        """
        link_params = {}
        # Use the instance kwargs as URL parameters
        link_params.update(self.kwargs)
        # Add keyword arguments from pager() to the link as parameters
        link_params.update(self.pager_kwargs)
        link_params[self.page_param] = pagenr

        # Create the URL to load the page area part of a certain page (AJAX updates)
        partial_url = link_params.pop('partial', '')

        # Create the URL to load a certain page
        link_url = link_params.pop('link', request.path_info)
        link_url = Markup(url(link_url, params=link_params))

        if self.onclick: # create link with onclick action for AJAX
            try: # if '%s' is used in the 'onclick' parameter (backwards compatibility)
                onclick_action = self.onclick % (partial_url,)
            except TypeError:
                onclick_action = string.Template(self.onclick).safe_substitute({
                  "partial_url": partial_url,
                  "page": pagenr
                })
            return _make_tag(self.page_link_template, text, href=link_url, onclick=onclick_action, **self.link_attr)
        else: # return static link
            return _make_tag(self.page_link_template, text, href=link_url, **self.link_attr)

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __json__(self):
        return {'total':self.item_count, 
                'page':self.page, 
                'items_per_page':self.items_per_page, 
                'entries':self.items}
