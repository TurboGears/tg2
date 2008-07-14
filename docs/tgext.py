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

import pysvn
import nose
from mercurial import hg, ui

 
beginmarker_re = re.compile(r'##\{(?P<section>.+)}')
endmarker_re = re.compile(r'##')

# This is based on 'Multi-line string block formatting' recipe by Brett Levin
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/145672
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
    """ Class that represents a Mercurial client """
    def __init__(self, path):
        self.repo = hg.repository(ui.ui(interactive=False), path=path)

    def get_file(self, path, revision='tip'):
        return self.repo.changectx(revision).filectx(path).data()

    
class SVNClient:
    """ Class that represents a Subversion client """
    def __init__(self):
        self.client = pysvn.Client()

    def get_file(self, path, revision='HEAD'):
        if revision == 'HEAD':
            return self.client.cat(path,
                                   pysvn.Revision(pysvn.opt_revision_kind.head))
        else:
            return self.client.cat(path,
                                   pysvn.Revision(pysvn.opt_revision_kind.number,
                                                  str(revision)))


def get_file(path, revision = None, type = None, repository = None):
    """ Read file from local filesystem of from a SCM repository. """
    if revision:
        if type == 'svn':
            scm = SVNClient()
        elif type == 'hg':
            scm = HgClient(repository)
        else:
            raise Exception, "SCM tool not correctly specified"
        data = scm.get_file(path, revision).splitlines()
    else:
        fp = open(path)
        data = fp.read().splitlines()
        fp.close()
    return data


# code directive
def code_directive(name, arguments, options, content, lineno,
                        content_offset, block_text, state, state_machine):
    if not state.document.settings.file_insertion_enabled:
        return [state.document.reporter.warning('File insertion disabled',
                                                line=lineno)]
    environment = state.document.settings.env
    file_name = arguments[0]
    if file_name.startswith('/'):
        file_path = file_name
    else:
        file_path = os.path.normpath(os.path.join(environment.config.code_path,
                                                  file_name))
    
    try:
        if options.has_key('revision'):
            data = get_file(file_path, options['revision'],
                            environment.config.code_scm,
                            environment.config.code_path)
        else:
            data = get_file(file_path)
        if options.has_key('section'):
            section = options['section']
            source = format_block(search(data, section))
        else:
            source = format_block('\n'.join(data))
        retnode = nodes.literal_block(source, source)
        retnode.line = 1   
    except Exception, e:
        retnode = state.document.reporter.warning(
            'Reading file %r failed: %r' % (arguments[0], str(e)), line=lineno)
    else:
        if options.has_key('test'):
            test = options['test']
            if test.startswith('/'):
                result = nose.run(argv = [__file__, options['test']])
            else:
                result = nose.run(argv = [__file__, environment.config.test_path
                                          + options['test']])
            if not result:
                retnode = state.document.reporter.warning(
                    'Test(s) associated to %r failed' % (arguments[0],),
                    line=lineno)
        if options.has_key('language'):
            retnode['language'] = options['language']
    return [retnode]

def setup(app):
    code_options = {'section': directives.unchanged, 
                    'language': directives.unchanged,
                    'test': directives.unchanged,
                    'revision': directives.unchanged}
    app.add_config_value('code_path', '', True)
    app.add_config_value('code_scm', '', True)
    app.add_config_value('test_path', '', True)
    app.add_directive('code', code_directive, 1, (1, 0, 1),  **code_options)
