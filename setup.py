#!/usr/bin/env python3

from setuptools import setup
setup(
    name = 'cryptobot',
    version = '1.0.0',
    license = 'Proprietary',
    description = 'a proprietary cryptocurrency trading bot',
    author = 'Aaron Esau',
    author_email = 'python@aaronesau.com',
    packages = ['cryptobot'],
    scripts = ['scripts/cryptobot'],
    python_requires = '>=3.6'
)
