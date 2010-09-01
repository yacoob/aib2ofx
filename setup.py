#!/usr/bin/env python

from setuptools import setup

setup(name='aib2ofx',
      description='Download data from aib.ie in OFX format',
      version='0.1',
      author='Jakub Turski',
      author_email='yacoob@gmail.com',
      url='http://github.com/yacoob/aib2ofx',

      install_requires=['BeautifulSoup', 'mechanize'],

      packages=['aib2ofx_lib'],
      scripts=['aib2ofx'],
     );
