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
import zipfile
import string

from docutils import nodes, utils
from docutils.parsers.rst import directives, roles, states
from docutils.statemachine import ViewList

from sphinx import util

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

def code_directive(name, arguments, options, content, lineno,
                        content_offset, block_text, state, state_machine):
    """ Directive to handle code sample related stuf   """
    if not state.document.settings.file_insertion_enabled:
        return [state.document.reporter.warning('File insertion disabled',
                                                line=lineno)]
    environment = state.document.settings.env
    file_name = arguments[0]
    if file_name.startswith(os.sep):
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
            if test.startswith(os.sep):
                result = nose.run(argv = [__file__, test])
            else:
                result = nose.run(argv = [__file__
                                          , os.path.join(environment.config.test_path
                                          , test)])
            if not result:
                retnode = state.document.reporter.warning(
                    'Test associated to %r failed' % (file_name,),
                    line=lineno)
        if options.has_key('language'):
            retnode['language'] = options['language']
    return [retnode]


def test_directive(name, arguments, options, content, lineno,
                        content_offset, block_text, state, state_machine):
    """ Directive to test code from external files """
    environment = state.document.settings.env
    
    test = arguments[0]
    if not test.startswith(os.sep):
        test = os.path.join(environment.config.test_path, test)
        
    if options.has_key('options'):
        opts = options['options'].split(',')
        # adjust the options to nose
        opts = map(lambda s: "--%s" % s.strip(), opts)
        
        opts.append(test)
    else:
        opts = [test]
    
    opts.insert(0, __file__)
    result = nose.run(argv = opts)
    if not result:
        retnode = state.document.reporter.warning(
                'Test %r failed' % (test,),
                line=lineno)
        return retnode
    return

def archive_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    archive = options['archive']
    return [nodes.reference(rawtext, utils.unescape(text), refuri=archive,
                            **options)], []

role_name = 'arch'

def archive_directive(name, arguments, options, content, lineno,
         content_offset, block_text, state, state_machine):
    """ Directive to create a archive (zip) from a sample project """
    environment = state.document.settings.env
    static_path = environment.config.html_static_path[0]
    
    directory = arguments[0]
    
    if options.has_key('file'):
        filename = options['file']
    else:
        filename = os.path.basename(directory.rstrip(os.sep)) + '.zip'
        
    archive_file = zipfile.ZipFile(os.path.dirname(os.path.abspath(__file__))
                        + '%s%s%s' % (os.sep, static_path, os.sep)
                        + filename, "w")
    
    if directory.startswith(os.sep):
        dir = directory
    else:
        dir = os.path.normpath(os.path.join(environment.config.code_path,
                    directory))
        
    for root, dirs, files in os.walk(dir,topdown=False):
        for name in files:
            file = os.path.join(root, name)
            zipfilename = string.replace(file, dir, '')
            if zipfilename[0] == os.sep:
                zipfilename = zipfilename[1:]
            archive_file.write(file, str(zipfilename), zipfile.ZIP_DEFLATED)

    archive_file.close()

    archive = util.relative_uri(state_machine.document.current_source,
                                os.path.dirname(os.path.abspath(__file__))
                        + '%s%s%s' % (os.sep, static_path, os.sep)) \
                        + filename

    role = roles.CustomRole(role_name, archive_role,
                            {'archive' : archive},
                            content)
    roles.register_local_role(role_name, role)
    return


def setup(app):
    code_options = {'section': directives.unchanged, 
                    'language': directives.unchanged,
                    'test': directives.unchanged,
                    'revision': directives.unchanged}
    test_options = {'options': directives.unchanged}
    archive_options = {'file': directives.unchanged}
    
    app.add_config_value('code_path', '', True)
    app.add_config_value('code_scm', '', True)
    app.add_directive('code', code_directive, 1, (1, 0, 1),  **code_options)
    
    app.add_directive('test', test_directive, 1, (1, 0, 1),  **test_options)
    app.add_config_value('test_path', '', True)

    app.add_directive('archive', archive_directive, 1, (1, 0, 1), **archive_options)
    
