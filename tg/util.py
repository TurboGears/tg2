"""Utilities"""
from pylons import config
import os, sys
import pkg_resources

def get_project_meta(name):
    for dirname in os.listdir("./"):
        if dirname.lower().endswith("egg-info"):
            fname = os.path.join(dirname, name)
            return fname

def get_project_name():
    """get project name if exist"""
    pkg_info = get_project_meta('PKG-INFO')
    if pkg_info:
        name = list(open(pkg_info))[1][6:-1]
        return name.strip()

def get_package_name():
    """Try to find out the package name of the current directory."""
    package = config.get("modules")
    if package:
        return package
    
    if "--egg" in sys.argv:
        projectname = sys.argv[sys.argv.index("--egg")+1]
        egg = pkg_resources.get_distribution(projectname)
        top_level = egg._get_metadata("top_level.txt")
    else:
        fname = get_project_meta('top_level.txt')
        top_level = fname and open(fname) or []
    
    for package in top_level:
        package = package.rstrip()
        if package and package != 'locales':
            return package
