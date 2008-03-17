try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='tgtest',
    version="",
    #description='',
    #author='',
    #author_email='',
    #url='',
    install_requires=[
        "TurboGears2",
        ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='nose.collector',
    package_data={'TGTest': ['i18n/*/LC_MESSAGES/*.mo',
                                 'templates/*/*',
                                 'public/*/*']},
    #message_extractors = {'TGTest': [
    #        ('**.py', 'python', None),
    #        ('templates/**.mako', 'mako', None),
    #        ('templates/**.html', 'genshi', None),
    #        ('public/**', 'ignore', None)]},
    entry_points="""
    [paste.app_factory]
    main = TGTest.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller
    """,
)
