# -*- coding: utf-8 -*-
"""
    TurboGears Documentation Extensions
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Extensions to improve documentation management and effectiveness.

    :copyright: Copyright 2008 by Bruno Melo.
    :license: MIT.
"""

import re
import os
import sys

from docutils import nodes
from docutils.parsers.rst import directives

try:
    from pysvn import Client, ClientError, Revision, opt_revision_kind
except ImportError:
    pass

beginmarker_re = re.compile(r'##\{(?P<section>.+)}')
endmarker_re = re.compile(r'##')

def format_block(block):
    """Format the given block of text, trimming leading/trailing
    empty lines and any leading whitespace that is common to all lines.
    The purpose is to let us list a code block as a multiline,
    triple-quoted Python string, taking care of indentation concerns."""
    # separate block into lines
    lines = str(block).split('\n')
    # remove leading/trailing empty lines
    while lines and not lines[0]:  del lines[0]
    while lines and not lines[-1]: del lines[-1]
    # look at first line to see how much indentation to trim
    ws = re.match(r'\s*',lines[0]).group(0)
    if ws:
        lines = map( lambda x: x.replace(ws,'',1), lines )
    # remove leading/trailing blank lines (after leading ws removal)
    # we do this again in case there were pure-whitespace lines
    while lines and not lines[0]:  del lines[0]
    while lines and not lines[-1]: del lines[-1]
    return '\n'.join(lines)+'\n'

def search(source, section):
    """Search in `source` for a section as specified in markers ##{section}
    (begin marker) and ## (end marker) and extract the lines between them.
    """
    lineno = 0
    begin, end = 0, 0
    for line in source:
        if not begin:
            result = beginmarker_re.search(line)
            if result and result.group('section') == section:
                begin = lineno + 1
        elif not end:
            if beginmarker_re.search(line) or endmarker_re.search(line):
                end = lineno
        lineno += 1
    if not end:
        end = len(source)

    return '\n'.join([source[line] for line in xrange(begin, end) \
                    if not (beginmarker_re.search(source[line]) \
                            or endmarker_re.search(source[line])) ])


class HgClient:
    def __init__(self, path):
        from mercurial import hg, ui
        self.repo = hg.repository(ui.ui(interactive=False), path=path)

    def get_file(self, path, revision='tip'):
        return self.repo.changectx(rev).filectx(path).data()

    
class SVNClient:
    def __init__(self):
        self.client = Client()

    def get_file(self, path, revision='HEAD'):
        if revision == 'HEAD':
            return self.client.cat(path, Revision(opt_revision_kind.head))
        else:
            return self.client.cat(path, Revision(opt_revision_kind.number, str(revision)))



def code_directive(name, arguments, options, content, lineno,
                        content_offset, block_text, state, state_machine):
    if not state.document.settings.file_insertion_enabled:
        return [state.document.reporter.warning('File insertion disabled', line=lineno)]
    environment = state.document.settings.env
    fname = arguments[0]
    fpath = os.path.normpath(os.path.join(environment.config.code_path, fname))
    
    revision = options.get('revision', '')
    try:
        if revision:
            if environment.config.code_scm == 'svn':
                scm = SVNClient()
            elif environment.config.code_scm == 'hg':
                scm = HgClient(environment.config.code_path)
            data = scm.get_file(fpath, revision).splitlines()
        else:
            fp = open(fpath)
            data = fp.read().splitlines()
            fp.close()
        section_name = options.get('section', '')
        source = format_block(search(data, section_name))
        retnode = nodes.literal_block(source, source)
    except Exception, e:
        retnode = state.document.reporter.warning(
            'Reading file %r failed: %r' % (arguments[0], str(e)), line=lineno)
    else:
        retnode.line = 1   
        if options.get('language', ''):
            retnode['language'] = options['language']
    return [retnode]

def setup(app):
    code_options = {'section': directives.unchanged, 
                    'language': directives.unchanged,
                    'revision': directives.unchanged}
    app.add_config_value('code_path', '', True)
    app.add_config_value('code_scm', '', True)
    app.add_directive('code', code_directive, 1, (1, 0, 1),  **code_options)
