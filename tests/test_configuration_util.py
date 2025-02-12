# -*- coding: utf-8 -*-
import pytest

from tg.configuration.utils import DependenciesList, DictionaryView


class DLEntry1: pass
class DLEntry2: pass
class DLEntry3: pass
class DLEntry4: pass
class DLEntry5: pass


class TestDependenciesList(object):
    def test_basic_with_classes(self):
        dl = DependenciesList()

        dl.add(DLEntry2)
        dl.add(DLEntry4, after=DLEntry3)
        dl.add(DLEntry3)
        dl.add(DLEntry1, after=False)
        dl.add(DLEntry5, after=DLEntry3)

        dl_values = list(dl.values())
        assert dl_values[0] == DLEntry1
        assert dl_values[1] == DLEntry2
        assert dl_values[2] == DLEntry3
        assert dl_values[3] == DLEntry4
        assert dl_values[4] == DLEntry5

    def test_basic_iter(self):
        dl = DependenciesList()

        dl.add(DLEntry2)
        dl.add(DLEntry4, after=DLEntry3)
        dl.add(DLEntry3)
        dl.add(DLEntry1, after=False)
        dl.add(DLEntry5, after=DLEntry3)

        visisted = []
        for key, value in dl:
            visisted.append(key)

        assert visisted == ['DLEntry1', 'DLEntry2', 'DLEntry3', 'DLEntry4', 'DLEntry5']

    def test_basic_repr(self):
        dl = DependenciesList()

        dl.add(DLEntry2)
        dl.add(DLEntry4, after=DLEntry3)
        dl.add(DLEntry3)
        dl.add(DLEntry1, after=False)
        dl.add(DLEntry5, after=DLEntry3)

        expected = "<DependenciesList ['DLEntry1', 'DLEntry2', 'DLEntry3', 'DLEntry4', 'DLEntry5']>"
        assert repr(dl) == expected

    def test_basic_with_ids(self):
        dl = DependenciesList()

        dl.add(DLEntry2, 'num2')
        dl.add(DLEntry4, 'num4', after='num3')
        dl.add(DLEntry3, 'num3')
        dl.add(DLEntry1, 'num1', after=False)
        dl.add(DLEntry5, 'num5', after='num3')

        dl_values = list(dl.values())
        assert dl_values[0] == DLEntry1
        assert dl_values[1] == DLEntry2
        assert dl_values[2] == DLEntry3
        assert dl_values[3] == DLEntry4
        assert dl_values[4] == DLEntry5

    def test_reversed_with_ids(self):
        dl = DependenciesList()

        dl.add(DLEntry5, 'num5', after='num4')
        dl.add(DLEntry4, 'num4', after='num3')
        dl.add(DLEntry3, 'num3', after='num2')
        dl.add(DLEntry2, 'num2', after='num1')
        dl.add(DLEntry1, 'num1')

        dl_values = list(dl.values())
        assert dl_values[0] == DLEntry1
        assert dl_values[1] == DLEntry2
        assert dl_values[2] == DLEntry3
        assert dl_values[3] == DLEntry4
        assert dl_values[4] == DLEntry5

    def test_multiple_with_ids(self):
        dl = DependenciesList()
        dl.add(DLEntry1)
        dl.add(DLEntry4, after=DLEntry3)
        dl.add(DLEntry5, after=DLEntry4)
        dl.add(DLEntry2, after=DLEntry1)
        dl.add(DLEntry3, after=DLEntry1)

        dl_values = list(dl.values())
        assert dl_values[0] == DLEntry1
        assert dl_values[1] == DLEntry2
        assert dl_values[2] == DLEntry3
        assert dl_values[3] == DLEntry4
        assert dl_values[4] == DLEntry5

    def test_multiple_with_missing_step(self):
        dl = DependenciesList()
        dl.add(DLEntry1)
        dl.add(DLEntry3, after=DLEntry2)
        dl.add(DLEntry2, after=DLEntry5)

        dl_values = list(dl.values())
        assert dl_values[0] == DLEntry1
        assert dl_values[1] == DLEntry2
        assert dl_values[2] == DLEntry3

    def test_objects_instead_of_classes(self):
        dl = DependenciesList()
        dl.add(DLEntry1(), 'DLEntry1')
        dl.add(DLEntry3(), 'DLEntry3', after=DLEntry2)
        dl.add(DLEntry2(), 'DLEntry2', after=DLEntry5)

        dl_values = list(dl.values())
        assert dl_values[0].__class__ == DLEntry1
        assert dl_values[1].__class__ == DLEntry2
        assert dl_values[2].__class__ == DLEntry3

    def test_objects_must_have_key(self):
        dl = DependenciesList()

        with pytest.raises(ValueError):
            dl.add(DLEntry1())

    def test_after_cannot_be_an_instance(self):
        dl = DependenciesList()
        dl.add(DLEntry1(), key='DLEntry1')
        with pytest.raises(ValueError):
            dl.add(DLEntry2(), key='DLEntry2', after=DLEntry1())

    def test_after_everything_else(self):
        dl = DependenciesList()

        dl.add(DLEntry2, after=True)
        dl.add(DLEntry5, after=True)
        dl.add(DLEntry4, after=DLEntry3)
        dl.add(DLEntry3, after=DLEntry2)

        dl.add(DLEntry1)

        dl_values = list(dl.values())
        assert dl_values[0] == DLEntry1
        assert dl_values[1] == DLEntry2
        assert dl_values[2] == DLEntry3
        assert dl_values[3] == DLEntry4
        assert dl_values[4] == DLEntry5

    def test_replacing_elements_with_key(self):
        dl = DependenciesList()

        dl.add(DLEntry2, 'num2')
        dl.add(DLEntry4, 'num4', after='num3')
        dl.add(DLEntry3, 'num3')
        dl.add(DLEntry1, 'num1', after=False)
        dl.add(DLEntry5, 'num5', after='num3')

        dl.replace('num3', DLEntry1)

        dl_values = list(dl.values())
        assert dl_values[0] == DLEntry1
        assert dl_values[1] == DLEntry2
        assert dl_values[2] == DLEntry1
        assert dl_values[3] == DLEntry4
        assert dl_values[4] == DLEntry5

    def test_replacing_elements_with_classes(self):
        dl = DependenciesList()

        dl.add(DLEntry2)
        dl.add(DLEntry4, after=DLEntry3)
        dl.add(DLEntry3)
        dl.add(DLEntry1, after=False)
        dl.add(DLEntry5, after=DLEntry3)

        dl.replace(DLEntry3, DLEntry1)

        dl_values = list(dl.values())
        assert dl_values[0] == DLEntry1
        assert dl_values[1] == DLEntry2
        assert dl_values[2] == DLEntry1
        assert dl_values[3] == DLEntry4
        assert dl_values[4] == DLEntry5

    def test_replace_key_check(self):
        dl = DependenciesList()

        with pytest.raises(ValueError):
            dl.replace(object(), object())

    def test_construction(self):
        dl = DependenciesList(DLEntry2, DLEntry1)

        dl.replace(DLEntry1, DLEntry3)

        dl_values = list(dl.values())
        assert dl_values[0] == DLEntry2
        assert dl_values[1] == DLEntry3

    def test_add_twice(self):
        dl = DependenciesList()

        dl.add(DLEntry2)
        with pytest.raises(KeyError):
            dl.add(DLEntry2)

    def test_get_by_class(self):
        dl = DependenciesList()

        dl.add(DLEntry2)
        assert issubclass(dl.get(DLEntry2), DLEntry2)

    def test_get_by_invalid_type(self):
        dl = DependenciesList()

        with pytest.raises(ValueError):
            dl.get(5)

    def test_get_missing(self):
        dl = DependenciesList()
        assert dl.get('MISSING') == None


class TestDictionaryView(object):
    def test_dictionary_view(self):
        d = DictionaryView({
            'test.one': 1,
            'test.two': 2
        }, 'test.')
        assert d['one'] == 1
        assert d.one == 1

    def test_dictionary_view_missing_attr(self):
        d = DictionaryView({}, '')

        with pytest.raises(AttributeError):
            d.missing

    def test_dictionary_view_missing_key(self):
        d = DictionaryView({}, '')

        with pytest.raises(KeyError):
            d['missing']

    def test_dictionary_set_attr(self):
        d = DictionaryView({}, 'test.')
        d.new = 5
        assert d.new == 5

    def test_dictionary_update(self):
        d = DictionaryView({}, 'test.')
        d.update({
            'a': 5
        })
        d.update([('b', 6)])
        d.update({}, c=7)

        assert d.a == 5
        assert d.b == 6
        assert d.c == 7
