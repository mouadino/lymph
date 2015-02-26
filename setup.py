# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

import sys


with open('README.rst') as f:
    description = f.read()

install_requires = [
    'docopt',
    'kazoo',
    'kombu',
    'gevent',
    'msgpack-python',
    'psutil',
    'PyYAML',
    'pyzmq',
    'redis',
    'setproctitle',
    'six',
    'Werkzeug',
    'blessings',
    'netifaces'
]

dependency_links = []

if sys.version_info.major == 2:
    install_requires.append('monotime')
elif sys.version_info.major == 3:
    # Installing Cython==0.20.1 for building gevent
    from setuptools.command.easy_install import main as easy_install
    easy_install(['Cython==0.20.1'])
    dependency_links.append(
        'git+https://github.com/gevent/gevent.git#egg=gevent-1.0.1')

setup(
    name='lymph',
    url='http://github.com/deliveryhero/lymph/',
    version='0.1.0',
    namespace_packages=['lymph'],
    packages=find_packages(),
    license=u'Apache License (2.0)',
    author=u'Delivery Hero Holding GmbH',
    maintainer=u'Johannes Dollinger',
    maintainer_email=u'johannes.dollinger@deliveryhero.com',
    long_description=description,
    include_package_data=True,
    install_requires=install_requires,
    dependency_links=dependency_links,
    extras_require={
        'sentry': ['raven'],
        'newrelic': ['newrelic'],
    },
    entry_points={
        'console_scripts': ['lymph = lymph.cli.main:main'],
        'lymph.cli': [
            'help = lymph.cli.help:HelpCommand',
            'list = lymph.cli.base:ListCommand',
            'tail = lymph.cli.tail:TailCommand',
            'instance = lymph.cli.service:InstanceCommand',
            'node = lymph.cli.service:NodeCommand',
            'request = lymph.cli.request:RequestCommand',
            'discover = lymph.cli.request:DiscoverCommand',
            'inspect = lymph.cli.request:InspectCommand',
            'subscribe = lymph.cli.request:SubscribeCommand',
            'emit = lymph.cli.request:EmitCommand',
            'shell = lymph.cli.shell:ShellCommand',
        ],
        'nose.plugins.0.10': ['lymph = lymph.testing.nose:LymphPlugin'],
        'pytest11': ['lymph = lymph.testing.pytest'],
        'kombu.serializers': [
            'lymph-json = lymph.serializers.kombu:json_serializer_args',
            'lymph-msgpack = lymph.serializers.kombu:msgpack_serializer_args',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3'
    ]
)
