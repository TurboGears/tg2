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
        'Pylons==dev,<0.9.7',
        'Genshi>=0.4',A
        'SQLAAlchemy>=0.3',
    ],
    extras_require={
        'core-testing':["nose", "TurboKid", "TurboJson"]
    },
    entry_points='''
        [paste.paster_create_template]
        turbogears2=tg.pastetemplate:TurboGearsTemplate
        [paste.global_paster_command]
        tginfo = tg.commands.info:InfoCommand
        quickstart = tg.commands.quickstart:QuickstartCommand
        
        [turbogears2.template]
        turbogears2=tg.pastetemplate:TurboGearsTemplate
        [turbogears2.command]
        tginfo = tg.commands.info:InfoCommand
        quickstart = tg.commands.quickstart:QuickstartCommand
        serve = paste.script.serve:ServeCommand [Config]
        shell = pylons.commands:ShellCommand
    ''',
)
