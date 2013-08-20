from datetime import datetime
from email.utils import parsedate_tz, mktime_tz
import mimetypes
from time import gmtime, time
from os.path import normcase, normpath, join, isfile, getmtime, getsize
from webob.exc import HTTPNotFound, HTTPForbidden, HTTPBadRequest
from repoze.lru import LRUCache

_BLOCK_SIZE = 4096 * 64 # 256K

mimetypes.init()

class _FileIter(object):
    def __init__(self, file, block_size):
        self.file = file
        self.block_size = block_size

    def __iter__(self):
        return self

    def next(self):
        val = self.file.read(self.block_size)
        if not val:
            raise StopIteration
        return val

    __next__ = next # py3

    def close(self):
        self.file.close()

class FileServeApp(object):
    """
    Serves a static filelike object.
    """
    def __init__(self, path, cache_max_age):
        self.path = path

        try:
            self.last_modified = getmtime(path)
            self.content_length = getsize(path)
        except (IOError, OSError):
            self.path = None

        if self.path is not None:
            content_type, content_encoding = mimetypes.guess_type(path, strict=False)
            if content_type is None:
                content_type = 'application/octet-stream'

            self.content_type = content_type
            self.content_encoding = content_encoding

        if cache_max_age is not None:
            self.cache_expires = cache_max_age

    def generate_etag(self):
        return '"%s-%s"' % (self.last_modified, self.content_length)

    def parse_date(self, value):
        try:
            return mktime_tz(parsedate_tz(value))
        except (TypeError, OverflowError):
            raise HTTPBadRequest(("Received an ill-formed timestamp for %s: %s\r\n") % (self.path, value))

    @classmethod
    def make_date(cls, d):
        if isinstance(d, datetime):
            d = d.utctimetuple()
        else:
            d = gmtime(d)

        return '%s, %02d%s%s%s%s %02d:%02d:%02d GMT' % (
            ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[d.tm_wday],
            d.tm_mday, ' ',
            ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
             'Oct', 'Nov', 'Dec')[d.tm_mon - 1],
            ' ', str(d.tm_year), d.tm_hour, d.tm_min, d.tm_sec)


    def has_been_modified(self, environ, etag, last_modified):
        if environ['REQUEST_METHOD'] not in ('GET', 'HEAD'):
            return False

        unmodified = False

        modified_since = environ.get('HTTP_IF_MODIFIED_SINCE')
        if modified_since:
            modified_since = self.parse_date(modified_since)
            if last_modified and last_modified <= modified_since:
                unmodified = True

        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match and etag == if_none_match:
            unmodified = True

        return not unmodified

    def __call__(self, environ, start_response):
        try:
            file = open(self.path, 'rb')
        except (IOError, OSError, TypeError) as e:
            return HTTPForbidden('You are not permitted to view this file (%s)' % e)(environ, start_response)

        headers = []
        timeout = self.cache_expires
        etag = self.generate_etag()
        headers += [('Etag', '%s' % etag),
            ('Cache-Control', 'max-age=%d, public' % timeout)]

        if not self.has_been_modified(environ, etag, self.last_modified):
            file.close()
            start_response('304 Not Modified', headers)
            return []

        headers.extend((
            ('Expires', self.make_date(time() + timeout)),
            ('Content-Type', self.content_type),
            ('Content-Length', str(self.content_length)),
            ('Last-Modified', self.make_date(self.last_modified))
            ))
        start_response('200 OK', headers)
        return environ.get('wsgi.file_wrapper', _FileIter)(file, _BLOCK_SIZE)

INVALID_PATH_PARTS = set(['..', '.']).intersection

class StaticsMiddleware(object):
    def _adapt_path(self, path):
        return normcase(normpath(path))

    def __init__(self, app, root_dir, cache_max_age=3600):
        self.app = app
        self.cache_max_age = cache_max_age
        self.doc_root = self._adapt_path(root_dir)
        self.paths_cache = LRUCache(1024)

    def __call__(self, environ, start_response):
        full_path = environ['PATH_INFO']
        filepath = self.paths_cache.get(full_path)

        if filepath is None:
            path = full_path.split('/')
            if INVALID_PATH_PARTS(path):
                return HTTPNotFound('Out of bounds: %s' % environ['PATH_INFO'])(environ, start_response)
            filepath = self._adapt_path(join(self.doc_root, *path))
            self.paths_cache.put(full_path, filepath)

        if isfile(filepath):
            return FileServeApp(filepath, self.cache_max_age)(environ, start_response)

        return self.app(environ, start_response)

