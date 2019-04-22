"""Setup data for aib2ofx."""

from setuptools import setup

setup(
    name='aib2ofx',
    description='Download data from aib.ie in OFX format',
    version='0.6',
    author='Jakub Turski',
    author_email='yacoob@gmail.com',
    url='http://github.com/yacoob/aib2ofx',
    packages=['aib2ofx'],
    entry_points={
        'console_scripts': ['aib2ofx = aib2ofx.main:main'],
    },
    install_requires=[
        'mechanicalsoup @ git+https://github.com/MechanicalSoup/MechanicalSoup@master#egg=mechanicalsoup-1.0.0-dev',
        'python-dateutil',
    ],
)
