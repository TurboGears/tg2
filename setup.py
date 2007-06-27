from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='TurboGears2',
    version=version,
    description='Next generation TurboGears',
    long_description='Next generation TurboGears built on Pylons',
    classifiers=[],
    keywords='turbogears pylons',
    author='Mark Ramm',
    author_email='mark.ramm@gmail.com',
    url='http://www.turbogears.org/',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'PasteScript>=1.3',
        'Pylons>0.9.5'
    ],
    entry_points='''
        [paste.paster_create_template]
        turbogears2=tg.pastetemplate:TurboGearsTemplate
        [paste.global_paster_command]
        quickstart = tg.command.quickstart:quickstart
    ''',
)