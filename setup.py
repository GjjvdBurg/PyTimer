import os

from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
        name = "PyTimer",
        version = "0.0.1",
        author = "Gertjan van den Burg",
        author_email = "gertjanvandenburg@gmail.com",
        description = ("A command line time tracking application"),
        license = "GPL v2",
        long_description = read("README.md"),
        install_requires = [
            'termcolor',
            'readchar',
            'dateutil'
            ],
        py_modules = ['pytimer'],
    )
