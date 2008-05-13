import paver.doctools
import paver.virtual
from setuptools import find_packages

execfile(path("tg") / "release.py")

options(
    sphinx=Bunch(
        
    ),
    virtualenv=Bunch(
    ),
    setup=Bunch(
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
        ],
        extras_require={
            'core-testing':["nose", "TurboKid", "TurboJson"]
        },
        entry_points='''
            [paste.global_paster_command]
            tginfo = tg.commands.info:InfoCommand
            [turbogears2.command]
            tginfo = tg.commands.info:InfoCommand
            serve = paste.script.serve:ServeCommand [Config]
            shell = pylons.commands:ShellCommand
        '''
    )
)

@task
@needs(["minilib", "generate_setup", "setuptools.command.sdist"])
def sdist():
    pass

@task
@needs(["minilib", "generate_setup", "setuptools.command.bdist_egg"])
def bdist_egg():
    pass
