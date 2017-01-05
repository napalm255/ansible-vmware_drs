#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup module."""

from setuptools import setup

with open('requirements.txt') as requirements_file:
    requirements = list(requirements_file.readlines())

setup(
    name='vmware_drs',
    version='0.1.0',
    description="Ansible VMWare DRS Module",
    long_description="Ansible VMWare DRS Module",
    author="Brad Gibson",
    author_email='napalm255@gmail.com',
    url='https://github.com/napalm255/ansible-vmware_drs',
    package_dir={'': 'library'},
    install_requires=requirements,
    license="BSD license",
    zip_safe=False,
    keywords='ansible-vmware_drs',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
