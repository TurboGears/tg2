import os
here = os.path.abspath(os.path.dirname(__file__))
execfile(os.path.join(here, 'tg', 'release.py'))

try:
    from setuptools import find_packages, setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import find_packages, setup

test_requirements = ['coverage',
                    'nose',
                    'TurboKid >= 1.0.4',
                    'zope.sqlalchemy >= 0.4',
                    'jinja2',
                    'chameleon.genshi',
                    'repoze.what >= 1.0.5',
                    'repoze.who-testutil >= 1.0rc1',
                    'wsgiref',
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
        'Pylons >= 0.9.7',
        'Genshi >= 0.5.1',
        'WebFlash >= 0.1a8',
        'ToscaWidgets >= 0.9.4',
        'WebError >= 0.10.1',
        'repoze.what-pylons >= 1.0rc3',
        'repoze.tm2 >= 1.0a4',
        'TurboJson >= 1.2.1',
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
