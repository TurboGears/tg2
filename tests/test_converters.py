from nose.tools import raises
from tg.support.converters import asbool, asint, aslist, astemplate

class TestAsBool(object):
    def test_asbool_truthy(self):
        assert asbool('true')
        assert asbool('yes')
        assert asbool('on')
        assert asbool('y')
        assert asbool('t')
        assert asbool('1')

    def test_asbool_falsy(self):
        assert not asbool('false')
        assert not asbool('no')
        assert not asbool('off')
        assert not asbool('n')
        assert not asbool('f')
        assert not asbool('0')

    @raises(ValueError)
    def test_asbool_broken(self):
        asbool('Test')

    @raises(ValueError)
    def test_nonstring(self):
        asint([True])


class TestAsInt(object):
    def test_fine(self):
        assert asint('55') == 55

    @raises(ValueError)
    def test_nan(self):
        asint('hello')

    @raises(ValueError)
    def test_nonstring(self):
        asint(['55'])


class TestAsList(object):
    def test_fine(self):
        assert aslist('first,   second, third', ',') == ['first', 'second', 'third']
        assert aslist('first second     third') == ['first', 'second', 'third']
        assert aslist('first,   second, third', ',', False) == ['first', '   second', ' third']

    def test_nonstring(self):
        assert aslist(55) == [55]

    def test_already_list(self):
        assert aslist([55]) == [55]

    def test_None(self):
        assert aslist(None) == []


class TestAsTemplate(object):
    def test_fine(self):
        assert hasattr(astemplate('You are ${name}'), 'substitute')
        assert astemplate('You are ${name}').substitute(name='John') == 'You are John'

    @raises(ValueError)
    def test_nonstring(self):
        astemplate(55)

    def test_aslready_template(self):
        assert astemplate(astemplate('You are ${name}')).substitute(name='John') == 'You are John'