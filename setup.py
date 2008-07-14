import os
here = os.path.abspath(os.path.dirname(__file__))
execfile(os.path.join(here, 'tg', 'release.py'))
from setuptools import find_packages, setup

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
        'Genshi',
        'Pylons>=0.9.7beta3',
        'ToscaWidgets>=0.9', 
    ],
    extras_require={
        'core-testing':["nose", "TurboKid", "TurboJson"]
    },
    entry_points='''
        [paste.global_paster_command]
        tginfo = tg.commands.info:InfoCommand
        [turbogears2.command]
        serve = paste.script.serve:ServeCommand [Config]
        shell = pylons.commands:ShellCommand
    '''
)