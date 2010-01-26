from tg.jsonify import jsonify, encode
from simplejson import loads
from datetime import date

class Person(object):
    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name
    
    @property
    def name(self):
        return '%s %s' % (self.first_name, self.last_name)
    
    def __json__(self):
        return dict(first_name=self.first_name, last_name=self.last_name)

def test_simple_rule():    
    # skip this test if simplegeneric is not installed
    try:
        import simplegeneric
    except ImportError:
        return
    
    # create a Person instance
    p = Person('Jonathan', 'LaCour')
    
    # encode the object using the existing "default" rules
    result = loads(encode(p))
    assert result['first_name'] == 'Jonathan'
    assert result['last_name'] == 'LaCour'
    assert len(result) == 2
    
    # register a generic JSON rule
    @jsonify.when_type(Person)
    def jsonify_person(obj):
        return dict(
            name=obj.name
        )
    
    # encode the object using our new rule
    result = loads(encode(p))
    assert result['name'] == 'Jonathan LaCour'
    assert len(result) == 1

def test_builtin_override():
    # skip this test if simplegeneric is not installed
    try:
        import simplegeneric
    except ImportError:
        return
    
    # create a few date objects
    d1 = date(1979, 10, 12)
    d2 = date(2000, 1, 1)
    d3 = date(2012, 1, 1)
    
    # jsonify using the built in rules
    result1 = encode(dict(date=d1))
    assert '"1979-10-12"' in result1
    result2 = encode(dict(date=d2))
    assert '"2000-01-01"' in result2
    result3 = encode(dict(date=d3))
    assert '"2012-01-01"' in result3
    
    # create a custom rule
    @jsonify.when_type(date)
    def jsonify_date(obj):
        if obj.year == 1979 and obj.month == 10 and obj.day == 12:
            return "Jon's Birthday!"
        elif obj.year == 2000 and obj.month == 1 and obj.day == 1:
            return "Its Y2K! Panic!"
        return '%d/%d/%d' % (obj.month, obj.day, obj.year)
    
    # jsonify using the built in rules
    result1 = encode(dict(date=d1))
    assert '"Jon\'s Birthday!"' in result1
    result2 = encode(dict(date=d2))
    assert '"Its Y2K! Panic!"' in result2
    result3 = encode(dict(date=d3))
    assert  '"1/1/2012"' in result3
