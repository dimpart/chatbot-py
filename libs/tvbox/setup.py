#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    TV Box
    ~~~~~~

    Live Stream
"""

import io

from setuptools import setup, find_packages

__version__ = '0.2.2'
__author__ = 'Albert Moky'
__contact__ = 'albert.moky@gmail.com'

with io.open('README.md', 'r', encoding='utf-8') as fh:
    readme = fh.read()

setup(
    name='tvbox',
    version=__version__,
    url='https://github.com/dimpart/chatbot-py',
    license='MIT',
    author=__author__,
    author_email=__contact__,
    description='TV Box: Live Stream',
    long_description=readme,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    package_data={
        '': ['res/*.js']
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    entry_points={
        'console_scripts': [
            'tvbox=tvbox.run:main',
        ]
    },
    install_requires=[
        'aiohttp',     # 3.9.5
        # 'aiosignal',   # 1.3.1
        # 'attrs',       # 23.2.0
        # 'frozenlist',  # 1.4.1
        # 'multidict',   # 6.0.5
        # 'yarl',        # 1.9.4

        'aiou>=0.1.0',
    ]
)
