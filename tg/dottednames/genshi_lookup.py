"""Reimplementation of the Genshi template loader that supports dotted names."""

import os
import stat

from genshi.template import TemplateLoader

import tg


class GenshiTemplateLoader(TemplateLoader):
    """Genshi template loader that supports
    zipped applications and dotted filenames as well as path names
    """

    def load(self, filename, relative_to=None, cls=None, encoding=None):
        """real loader function. copy paste from the mako template
        loader.
        """
        # TODO: get the template extension from the config!!
        if not filename.endswith('.html'):
            filename = tg.config['pylons.app_globals'
                    ].dotted_filename_finder.get_dotted_filename(
                            template_name=filename,
                            template_extension='.html')

        return TemplateLoader.load(self, filename,
                relative_to=relative_to, cls=cls, encoding=encoding)

