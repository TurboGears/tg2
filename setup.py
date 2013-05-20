import os
here = os.path.abspath(os.path.dirname(__file__))
exec(compile(open(os.path.join(here, 'tg', 'release.py')).read(), 'release.py', 'exec'), globals(), locals())

from setuptools import find_packages, setup

import sys
py_version = sys.version_info[:2]

if py_version < (2, 6):
    raise RuntimeError('TurboGears2 requires Python 2.6 or better')

if py_version[0] == 3 and py_version < (3, 2):
    raise RuntimeError('When using Python3 TurboGears2 requires at least Python3.2')

test_requirements = ['coverage',
                    'nose',
                    'zope.sqlalchemy >= 0.4',
                    'repoze.who',
                    'repoze.who.plugins.sa >= 1.0.1',
                    'Genshi >= 0.5.1',
                    'Mako',
                    'WebTest < 2.0',
                    'routes',
                    'backlash',
                    'sqlalchemy'
                    ]

if py_version == (3, 2):
    #jinja2 2.7 is incompatible with Python 3.2
    test_requirements.append('jinja2 < 2.7')
else:
    test_requirements.append('jinja2')


if py_version[0] == 2:
    test_requirements.extend(['TurboKid >= 1.0.4',
                              'Kajiki >= 0.2.2',
                              'Chameleon < 2.0a',
                              'simplegeneric',
                              'Formencode',
                              'routes',
                              'tgming',
                              'tw.forms',
                              'tw2.forms'])

install_requires=[
    'WebOb >= 1.2',
    'crank >= 0.6.2',
    'Beaker',
    'decorator',
    'PasteDeploy',
    'repoze.lru'
]

if py_version == (3, 2):
    #markupsafe 0.16 is incompatible with Python 3.2
    install_requires.append('MarkupSafe < 0.16')
else:
    install_requires.append('MarkupSafe')

setup(
    name='TurboGears2',
    version=version,
    description=description,
    long_description=long_description,
    classifiers=[],
    keywords='turbogears',
    author=author,
    author_email=email,
    url=url,
    license=license,
    packages=find_packages(exclude=['ez_setup', 'examples']),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
        #XXX: Perhaps this 'core-testing' extras_require can be removed
        #     since tests_require takes care of that as long as TG is tested
        #     with 'python setup.py test' (which we should IMHO so setuptools
        #     can take care of these details for us)
        'core-testing':test_requirements,
    },
    test_suite='nose.collector',
    tests_require = test_requirements,
    entry_points='''
    ''',
    dependency_links=[
        "http://tg.gy/230"
        ]
)
