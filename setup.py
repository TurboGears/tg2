import os
here = os.path.abspath(os.path.dirname(__file__))
execfile(os.path.join(here, 'tg', 'release.py'))
from setuptools import find_packages, setup

test_requirements = ['coverage',
                    'nose',
                    'repoze.tm2',
                    'TurboKid', 
                    'TurboJson', 
                    'zope.sqlalchemy',
                    'SQLAlchemy>=0.5beta3',
                    ]

setup(
    name='TurboGears2',
    version=version,
    description=description,
    long_description=long_description,
    classifiers=[],
    keywords='turbogears pylons',
    author=author,
    author_email=email,
    url=url,
    license=license,
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Babel',
        'decorator',
        'Genshi',
        'Pylons>=0.9.7beta3',
        'ToscaWidgets>=0.9',
        'repoze.what',
        'repoze.what.plugins.sql',
        'SQLAlchemy>=0.5beta3',
    ],
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
        [paste.global_paster_command]
        tginfo = tg.commands.info:InfoCommand
        [turbogears2.command]
        serve = paste.script.serve:ServeCommand [Config]
        shell = pylons.commands:ShellCommand
    '''
)
