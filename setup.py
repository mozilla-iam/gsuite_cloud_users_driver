#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = ['boto3', 'everett', 'google-api-python-client', 'oauth2client']

setup_requirements = ['pytest-runner']

test_requirements = ['jsonschema', 'mock', 'moto', 'pytest', 'pytest-watch', 'pytest-cov', 'flake8']

extras = {'test': test_requirements}

setup(
    name="gsuite_cloud_users_driver",
    version="0.0.1",
    author="Andrew Krug",
    author_email="akrug@mozilla.com",
    description="Lifecycle management for google cloud users driven by profilev2.",
    long_description=long_description,
    url="https://github.com/mozilla-iam/gsuite_cloud_users_driver",
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Mozilla Public License",
        "Operating System :: OS Independent",
    ),
    install_requires=requirements,
    license="Mozilla Public License 2.0",
    include_package_data=True,
    packages=find_packages(include=['gsuite_cloud_users_driver']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    extras_require=extras,
    zip_safe=False
)
