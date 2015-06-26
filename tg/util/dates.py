from datetime import timedelta, tzinfo, datetime
import re


TIMEDELTA_ZERO = timedelta(0)
DATETIME_RE = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r'(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$'
)


class _UTCTZ(tzinfo):
    """
    UTC implementation taken from Python's docs.
    """

    def __repr__(self):
        return "<{0}>".format(self.tzname(None))

    def utcoffset(self, dt):
        return TIMEDELTA_ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return TIMEDELTA_ZERO


#: UTC tzinfo instance
utctz = _UTCTZ()


class _FixedOffsetTZ(tzinfo):
    """
    Fixed offset in minutes east from UTC. Taken from Python's docs.
    """

    def __init__(self, offset=None, name=None):
        if offset is not None:
            self.__offset = timedelta(minutes=offset)
        if name is not None:
            self.__name = name

    def __repr__(self):
        return "<{0}>".format(self.tzname(None))

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return TIMEDELTA_ZERO


def get_fixed_timezone(offset):
    """
    Returns a tzinfo instance with a fixed offset from UTC.

    ``offset`` should be provided in minutes or as a ``timedelta``.
    """
    if isinstance(offset, timedelta):
        offset = offset.seconds // 60

    offset //= 1  # ensure it's more than a minute
    sign = '-' if offset < 0 else '+'
    hhmm = '%02d%02d' % divmod(abs(offset), 60)
    name = sign + hhmm
    return _FixedOffsetTZ(offset, name)


def parse_datetime(value):
    """Parses a string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.

    Raises ``ValueError`` if the input isn't well formatted.
    """
    match = DATETIME_RE.match(value)
    if not match:
        raise ValueError('Malformed date string')

    kw = match.groupdict()
    if kw['microsecond']:
        kw['microsecond'] = kw['microsecond'].ljust(6, '0')
    valuetz = kw.pop('tzinfo')
    if valuetz == 'Z':
        valuetz = utctz
    elif valuetz is not None:
        offset_mins = int(valuetz[-2:]) if len(valuetz) > 3 else 0
        offset = 60 * int(valuetz[1:3]) + offset_mins
        if valuetz[0] == '-':
            offset = -offset
        valuetz = get_fixed_timezone(offset)
    kw = dict((k, int(v)) for k, v in kw.items() if v is not None)
    kw['tzinfo'] = valuetz
    return datetime(**kw)
