# -*- coding: UTF-8 -*-

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
import sys, os

if sys.version_info < (2, 4):
    raise SystemExit("Python 2.4 or later is required")

execfile(os.path.join("tg", "release.py"))

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
        'Pylons',
        'Genshi>=0.4',
        'SQLAlchemy>=0.4',
        'ToscaWidgets>=0.2rc2',
        'tw.forms',
        'DBSprockets',
        'sqlalchemy-migrate >= 0.4.4',
        'tg.quickstart',
    ],
    extras_require={
        'core-testing':["nose", "TurboKid", "TurboJson"]
    },
    entry_points='''
        [paste.global_paster_command]
        tginfo = tg.commands.info:InfoCommand
        [paste.paster_command]
        crud = tg.commands.crud:CrudCommand
        migrate = tg.commands.migration:MigrateCommand
        [turbogears2.command]
        tginfo = tg.commands.info:InfoCommand
        crud = tg.commands.crud:CrudCommand
        serve = paste.script.serve:ServeCommand [Config]
        shell = pylons.commands:ShellCommand
    ''',
)
