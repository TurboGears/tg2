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
                    'backlash >= 0.0.7',
                    'sqlalchemy',
                    'raven < 4.1.0',
                    'formencode>=1.3.0a1',
                    'tw2.forms'
                    ]

if py_version == (3, 2):
    #jinja2 2.7 is incompatible with Python 3.2
    test_requirements.append('jinja2 < 2.7')
else:
    test_requirements.append('jinja2')


if py_version[0] == 2:
    test_requirements.extend(['TurboKid >= 1.0.4',
                              'Kajiki >= 0.2.2',
                              'routes',
                              'tgming',
                              'tw.forms'])

install_requires=[
    'WebOb >= 1.2',
    'crank >= 0.7.2, < 0.8',
    'Beaker',
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
    classifiers=[
        'Intended Audience :: Developers',
        'Environment :: Web Environment',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
    ],
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
       # Used by Travis and Coverage due to setup.py nosetests
       # causing a coredump when used with coverage
       'testing':test_requirements,
    },
    test_suite='nose.collector',
    tests_require = test_requirements,
    entry_points='''
    '''
)
