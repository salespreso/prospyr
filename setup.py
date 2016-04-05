#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from codecs import open

from setuptools import setup

# README.rst contents
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    readme = f.read()


# project version
context = {}
with open(os.path.join(here, 'prospyr/version.py')) as f:
    exec(f.read(), context)
    version = '.'.join(str(p) for p in context['VERSION'])


# requirements
def just_packages(path):
    with open(path, encoding='utf-8') as f:
        reqs = list(f)
    return [req.split('==')[0] for req in reqs
            if '==' in req and not req.startswith('#')]
requirements = just_packages(os.path.join(here, 'requirements'))
dev_requirements = just_packages(os.path.join(here, 'dev-requirements'))


setup(
    name='prospyr',
    description='ProsperWorks client library',
    long_description=readme,
    version=version,
    url='https://github.com/salespreso/prospyr/',
    author='Ben Graham',
    author_email='ben.graham@salespreso.com',
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='ProsperWorks',
    packages=['prospyr'],
    install_requires=requirements,
    extras_require={'dev': dev_requirements},
    test_suite='nose.core.collector',
    tests_require=dev_requirements,
)
