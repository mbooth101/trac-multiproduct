#!/usr/bin/env python
# Copyright (C) 2009 Mat Booth <mat@matbooth.co.uk>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from setuptools import setup

setup(
    name='MultiProduct',
    version='0.0.1',
    author='Mat Booth',
    author_email='mat@matbooth.co.uk',
    url='TODO',
    license='BSD',
    description='Multiple product support for Trac',
    long_description='TODO',
    packages=['multiproduct'],
    package_data={
        'multiproduct' : [
            'htdocs/css/*.css',
            'htdocs/js/*.js',
            'templates/*.html',
            ]
        },
    entry_points={
        'trac.plugins': [
           'multiproduct.admin = multiproduct.admin',
           'multiproduct.main = multiproduct.main',
           'multiproduct.model = multiproduct.model',
           ]
        },
    install_requires = [])
