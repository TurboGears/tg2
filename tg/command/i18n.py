# test-file: test_command_i18n.py

"""Command-line user interface for i18n administration."""

import re
import glob
import os
import os.path
import atexit
import optparse
import tempfile

from elementtree.ElementTree import ElementTree

import formencode
import turbogears
import turbogears.i18n
from turbogears.toolbox.admi18n import pygettext, msgfmt, catalog
from turbogears.toolbox.admi18n.catalog import quote, normalize
from turbogears.command.base import silent_os_remove
from turbogears.util import get_model, load_project_config, get_package_name
from pkg_resources import resource_filename

class ProgramError(StandardError):
    """Signals about a general application error."""

def copy_file(src, dest):
    if os.path.exists(dest):
        os.remove(dest)
    data = open(src, 'rb').read()
    open(dest, 'wb').write(data)

class InternationalizationTool:
    "Manages i18n data via command-line interface."

    desc = "Manage i18n data"
    need_project = True
    config = False

    name = None
    package = None
    __version__ = "0.2"
    __author__ = "Max Ischenko, U{http://maxischenko.in.ua}"
    __email__ = "ischenko@gmail.com"
    __copyright__ = "Copyright 2005-2006 Max Ischenko"
    __license__ = "MIT"

    def __init__(self, version):
        parser = optparse.OptionParser(usage="""
%prog [options] <command>

Available commands:
  add <locale>  Creates a message catalog for specified locale
  collect       Scan source files to gather translatable strings in a .pot file
  merge         Sync message catalog in different languages with .pot file
  compile       Compile message catalog (.po -> .mo)
  clean         Delete backups and compiled files
""", version="%prog " + self.__version__)
        parser.add_option("-f", "--force", default=False,
                action="store_true", dest="force_ops",
                help="Force potentially damaging actions")
        parser.add_option("-a", "--ascii", default=False,
                action="store_true", dest="ascii_output",
                help="Escape non-ascii characters")
        parser.add_option("-K", "--no-kid-support", default=True,
                action="store_false", dest="kid_support",
                help="Do not extract messages from Kid templates")
        parser.add_option("", "--loose-kid-support",
                action="store_true", dest="loose_kid_support",
                help="Extract ALL messages from Kid templates" \
                     " (this is default)")
        parser.add_option("", "--strict-kid-support",
                action="store_false", dest="loose_kid_support",
                help="Extract only messages marked with lang attribute " \
                     "from Kid templates")
        parser.add_option("", "--src-dir", default=None,
                action="store", dest="source_dir",
                help="Directory that contains source files")
        parser.set_defaults(loose_kid_support=True)
        self.parser = parser

    def load_project_config(self):
        """Chooses the config file, trying to guess whether this is a
        development or installed project."""

        # defaults
        self.locale_dir = 'locales'
        self.domain = 'messages'

        # check whether user specified custom settings
        if self.config:
            load_project_config()
 
        if turbogears.config.get("i18n.locale_dir"):
            self.locale_dir = turbogears.config.get("i18n.locale_dir")
            print 'Use %s as a locale directory' % self.locale_dir
        if turbogears.config.get('i18n.domain'):
            self.domain = turbogears.config.get("i18n.domain")
            print 'Use %s as a message domain' % self.domain

        if os.path.exists(self.locale_dir) and \
                not os.path.isdir(self.locale_dir):
                    raise ProgramError, \
                            ('%s is not a directory' % self.locale_dir)

        if not os.path.exists(self.locale_dir):
            os.makedirs(self.locale_dir)

    def parse_args(self):
        return self.parser.parse_args()

    def run(self):
        self.load_project_config()
        (options, args) = self.parse_args()
        if not args:
            self.parser.error("No command specified")
        self.options = options
        command, args = args[0], args[1:]
        if 'collect' == command:
            self.scan_source_files()
        elif 'add' == command:
            self.add_languages(args)
        elif 'compile' == command:
            self.compile_message_catalogs()
        elif 'merge' == command:
            self.merge_message_catalogs()
        elif 'clean' == command:
            self.clean_generated_files()
        else:
            self.parser.error("Command not recognized")
    def clean_generated_files(self):
        potfile = self.get_potfile_path()
        silent_os_remove(potfile.replace('.pot', '.bak'))
        for fname in self.list_message_catalogs():
            silent_os_remove(fname.replace('.po', '.mo'))
            silent_os_remove(fname.replace('.po', '.back'))
    def merge_message_catalogs(self):
        potfile = self.get_potfile_path()
        catalogs = self.list_message_catalogs()
        catalog.merge(potfile, catalogs)
    def compile_message_catalogs(self):
        for fname in self.list_message_catalogs():
            dest = fname.replace('.po','.mo')
            msgfmt.make(fname, dest)
            if os.path.exists(dest):
                print 'Compiled %s OK' % fname
            else:
                print 'Compilation of %s failed!' % fname

    def _copy_file_withcheck(self, sourcefile, targetfile):
        if not (os.path.exists(targetfile) and not self.options.force_ops):
            copy_file(sourcefile, targetfile)
            print 'Copy', sourcefile, 'to', targetfile
        else:
            print "File %s exists, use --force to override" % targetfile
            

    def _copy_moduletranslation(self, sourcefile, targetdir, language):
        modulefilename = os.path.basename(sourcefile)
        if os.path.exists(sourcefile):
            targetfile = os.path.join(targetdir, modulefilename)
            self._copy_file_withcheck(sourcefile, targetfile)
        else:
            print "%s translation for language '%s' does not exist (file searched '%s').\nPlease consider to contribute a translation." % (modulefilename, language, sourcefile)


    def add_languages(self, codes):
        potfile = self.get_potfile_path()
        if not os.path.isfile(potfile):
            print "Run 'collect' first to create", potfile
            return
        for code in codes:
            catalog_file = self.get_locale_catalog(code)
            langdir = os.path.dirname(catalog_file)
            if not os.path.exists(langdir):
                os.makedirs(langdir)
            sourcefile_fe = os.path.join(formencode.api.get_localedir(), code, \
                "LC_MESSAGES","FormEncode.mo")
            self._copy_moduletranslation(sourcefile_fe, langdir, code)

            basedir_i18n_tg = resource_filename("turbogears.i18n", "data")
            sourcefile_tg  = os.path.join(basedir_i18n_tg, code, \
                                          "LC_MESSAGES", "TurboGears.mo")
            self._copy_moduletranslation(sourcefile_tg, langdir, code)

            self._copy_file_withcheck(potfile, catalog_file)
                

        
    def scan_source_files(self):
        source_files = []
        kid_files = []
        srcdir = self.options.source_dir or get_package_name()
        print 'Scanning source directory', srcdir
        for root, dirs, files in os.walk(srcdir):
            if os.path.basename(root).lower() in ('CVS', '.svn'):
                continue
            for fname in files:
                name,ext = os.path.splitext(fname)
                srcfile = os.path.join(root, fname)
                if ext == '.py':
                    source_files.append(srcfile)
                elif ext == '.kid':
                    kid_files.append(srcfile)
                    #print 'add', srcfile
                else:
                    pass # do nothing
        (tmp_handle, tmp_potfile) = tempfile.mkstemp('.pot', 'tmp', self.locale_dir)
        os.close(tmp_handle)
        potbasename = os.path.basename(tmp_potfile)[:-4]
        pygettext_options = ['-v', '-d', potbasename, \
                '-p', os.path.dirname(tmp_potfile)]
        if self.options.ascii_output:
            pygettext_options.insert(0, '-E')
        pygettext.sys.argv = [''] + pygettext_options + source_files
        pygettext.main()
        if not os.path.exists(tmp_potfile):
            raise ProgramError, 'pygettext failed'
        atexit.register(silent_os_remove, tmp_potfile)
        if kid_files and self.options.kid_support:
            self.scan_kid_files(tmp_potfile, kid_files)
        potfile = self.get_potfile_path()
        if os.path.isfile(potfile):
            bakfile = potfile.replace('.pot', '.bak')
            silent_os_remove(bakfile)
            os.rename(potfile, bakfile)
            print 'Backup existing file to', bakfile
        os.rename(tmp_potfile, potfile)
        print 'Message templates written to', potfile
    def scan_kid_files(self, potfile, files):
        messages = []
        tags_to_ignore = ['script', 'style']
        keys = []
        kid_expr_re = re.compile(r"_\(('(?P<texta>[^']*)'|\"(?P<textb>[^\"]*)\")\)")
        for fname in files:
            print 'working on', fname
            tree = None
            try:
                tree = ElementTree(file=fname).getroot()
            except Exception, e:
                print 'Skip %s: %s' % (fname, e)
                continue
            for el in tree.getiterator():
                if self.options.loose_kid_support or el.get('lang', None):
                    tag = re.sub('({[^}]+})?(\w+)', '\\2', el.tag)
                    ents = []
                    if el.text: ents = [el.text.strip()]
                    if el.attrib: ents.extend(el.attrib.values())
                    for k in ents:
                        key = None
                        s = kid_expr_re.search(k)
                        if s:
                            key = s.groupdict()['texta'] or s.groupdict()['textb']
                        if key and (key not in keys) and (tag not in tags_to_ignore):
                            messages.append((tag, fname, key))
                            keys.append(key)
        fd = open(potfile, 'at+')
        for tag,fname,text in messages:
            text = normalize(text.encode('utf-8'))
            print >>fd, '#: %s:%s' % (fname, tag)
            print >>fd, 'msgid %s' % text
            print >>fd, 'msgstr ""'
            print >>fd, ''
        fd.close()
    def get_potfile_path(self):
        return os.path.join(self.locale_dir, '%s.pot' % self.domain)
    def get_locale_catalog(self, code):
        return os.path.join(self.locale_dir, code, 'LC_MESSAGES', '%s.po' % self.domain)
    def list_message_catalogs(self):
        files = []
        for name in glob.glob(self.locale_dir + '/*'):
            if os.path.isdir(name):
                fname = os.path.join(name, 'LC_MESSAGES', '%s.po' % self.domain)
                if os.path.isfile(fname):
                    files.append(fname)
        return files
    def fix_tzinfo(self, potfile):
        """
        In certain enviroments, tz info as formatted by strftime() is not utf-8.
        E.g. Windows XP with russian MUL.

        This leads to later error when a program trying to read catalog.
        """
        data = file(potfile, 'rb').read()
        def repl(m):
            "Remove tzinfo if it breaks encoding."
            tzinfo = m.group(2)
            try:
                tzinfo.decode('utf-8')
            except UnicodeDecodeError, e:
                return m.group(1) # cut tz info
            return m.group(0) # leave unchanged
        data = re.sub("(POT-Creation-Date: [\d-]+ [0-9:]+)\+([^\\\\]+)", repl, data)
        file(potfile, 'wb').write(data)

def main():
    tool = InternationalizationTool()
    tool.run()

if __name__ == '__main__':
    main()
