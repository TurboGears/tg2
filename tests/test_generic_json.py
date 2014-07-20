from tg.jsonify import encode, JSONEncoder
from datetime import date

from json import loads

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
    # create a Person instance
    p = Person('Jonathan', 'LaCour')
    
    # encode the object using the existing "default" rules
    result = loads(encode(p))
    assert result['first_name'] == 'Jonathan'
    assert result['last_name'] == 'LaCour'
    assert len(result) == 2
    
    person_encoder = JSONEncoder(custom_encoders={
        Person: lambda p: dict(name=p.name)
    })
   
    # encode the object using our new rule
    result = loads(encode(p, encoder=person_encoder))
    assert result['name'] == 'Jonathan LaCour'
    assert len(result) == 1


def test_custom_encoder_twice():
    # create a Person instance
    p = Person('Jonathan', 'LaCour')

    # encode the object using the existing "default" rules
    result = loads(encode(p))
    assert result['first_name'] == 'Jonathan'
    assert result['last_name'] == 'LaCour'
    assert len(result) == 2

    person_encoder = JSONEncoder(custom_encoders={
        Person: lambda p: dict(name=p.name)
    })

    person_encoder.register_custom_encoder(Person, lambda p: dict(fullname=p.name))

    # encode the object using our new rule
    result = loads(encode(p, encoder=person_encoder))
    assert result['fullname'] == 'Jonathan LaCour'
    assert len(result) == 1


def test_builtin_override():
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
    
    def jsonify_date(obj):
        if obj.year == 1979 and obj.month == 10 and obj.day == 12:
            return "Jon's Birthday!"
        elif obj.year == 2000 and obj.month == 1 and obj.day == 1:
            return "Its Y2K! Panic!"
        return '%d/%d/%d' % (obj.month, obj.day, obj.year)

    custom_date_encoder = JSONEncoder(custom_encoders={
        date: jsonify_date
    })

    
    # jsonify using the built in rules
    result1 = encode(dict(date=d1), encoder=custom_date_encoder)
    assert '"Jon\'s Birthday!"' in result1
    result2 = encode(dict(date=d2), encoder=custom_date_encoder)
    assert '"Its Y2K! Panic!"' in result2
    result3 = encode(dict(date=d3), encoder=custom_date_encoder)
    assert  '"1/1/2012"' in result3
