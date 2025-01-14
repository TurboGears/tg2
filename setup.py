import os
here = os.path.abspath(os.path.dirname(__file__))
exec(compile(open(os.path.join(here, 'tg', 'release.py')).read(), 'release.py', 'exec'), globals(), locals())

from setuptools import find_packages, setup

import sys
py_version = sys.version_info[:2]

if py_version < (3, 7):
    raise RuntimeError('TurboGears2 requires Python 3.7 or better')

test_requirements = ['pytest',
                     'zope.sqlalchemy >= 0.4',
                     'repoze.who',
                     'repoze.who.plugins.sa >= 1.0.1',
                     'Genshi >= 0.5.1',
                     'Mako',
                     'WebTest',
                     'backlash >= 0.3.0',
                     'raven',
                     'Beaker',
                     'sqlalchemy',
                     'jinja2',
                     'typing;python_version<"3.5"',
                     'ming >= 0.8.0',
                     'Kajiki >= 0.4.4',
                     'formencode>=1.3.0a1',]


install_requires=[
    'WebOb >= 1.8.0, < 1.10.0',
    'crank >= 0.8.0, < 0.9.0',
    'repoze.lru',
    'MarkupSafe'
]

setup(
    name='TurboGears2',
    version=version,
    description=description,
    long_description=long_description,
    classifiers=[
        'Intended Audience :: Developers',
        'Environment :: Web Environment',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
    ],
    keywords='turbogears',
    author=author,
    author_email=email,
    url=url,
    license=license,
    packages=find_packages(exclude=('ez_setup', 'examples', 'tests', 'tests.*')),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
       'testing':test_requirements,
    },
    entry_points='''
    '''
)
