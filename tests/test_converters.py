import logging

import pytest

from tg.support.converters import asbool, asint, aslist, aslogger, astemplate


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

    def test_asbool_broken(self):
        with pytest.raises(ValueError):
            asbool('Test')

    def test_nonstring(self):
        with pytest.raises(ValueError):
            asint([True])


class TestAsInt(object):
    def test_fine(self):
        assert asint('55') == 55

    def test_nan(self):
        with pytest.raises(ValueError):
            asint('hello')

    def test_nonstring(self):
        with pytest.raises(ValueError):
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

    def test_nonstring(self):
        with pytest.raises(ValueError):
            astemplate(55)

    def test_aslready_template(self):
        assert astemplate(astemplate('You are ${name}')).substitute(name='John') == 'You are John'


class TestAsLogger(object):
    def test_fine(self):
        assert aslogger('root') == logging.getLogger('root')

    def test_nonstring(self):
        with pytest.raises(ValueError):
            aslogger(55)

    def test_already_logger(self):
        assert aslogger(logging.getLogger('root')) == logging.getLogger('root')