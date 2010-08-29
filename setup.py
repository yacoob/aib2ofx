#!/usr/bin/env python

from distutils.core import setup

setup(name='aib2ofx',
      description='Download data from aib.ie in OFX format',
      version='0.1',
      author='Jakub Turski',
      author_email='yacoob@gmail.com',
      url='http://github.com/yacoob/aib2ofx',

      requires=['BeautifulSoup', 'mechanize'],

      packages=['aib2ofx'],
      scripts=['aib2ofx/aib2ofx.py'],
     );
