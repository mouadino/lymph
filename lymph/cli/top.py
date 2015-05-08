# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import time
import collections
import traceback

from blessings import Terminal

from lymph.client import Client
from lymph.cli.base import Command


class Table(object):

    def __init__(self, headers):
        self.headers = headers
        self.instances = []

    def display(self, terminal):
        for header, size in self.headers.items():
            header = self._truncate(header, size)
            print(terminal.bold(header), end=' ')
        print()  # flush
        for instance in self.instances:
            print(' '.join(self._truncate(getattr(instance, name), size) for name, size in self.headers.items()))
        print()  # flush

    @staticmethod
    def _truncate(name, size):
        name = str(name)
        if len(name) > size:
            return name[:size - 2] + ".."
        return name.ljust(size)


class InstanceInfo(collections.namedtuple('InstanceInfo', 'name endpoint metrics')):

    def __getattr__(self, name):
        return self.metrics[name]


class Debugger(object):
    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if type:
            traceback.print_exception(type, value, tb, file=sys.stdout)


class TopCommand(Command):
    """
    Usage: lymph top

    Show services metrics

    {COMMON_OPTIONS}

    """

    short_description = 'Show services metrics.'

    def run(self):
        with Debugger():
            terminal = Terminal()
            table = Table({
                'name': 15,
                'endpoint': 25,
                'greenlets.count': 20,
                'gevent.active': 20
            })

            with terminal.fullscreen():
                while True:
                    table.instances = self.get_instances()
                    table.display(terminal)
                    time.sleep(1)
                    print(terminal.clear, end='')

    def get_instances(self):
        self.client = Client.from_config(self.config)
        services = self.client.container.discover()
        instances = []
        for interface_name in sorted(services):
            interface_instances = self.client.container.lookup(interface_name)
            for instance in interface_instances:
                metrics = self.get_instance_metrics(instance)
                instances.append(
                    InstanceInfo(interface_name, instance.endpoint, metrics)
                )
        return instances

    def get_instance_metrics(self, instance):
        metrics = self.client.request(instance.endpoint, 'lymph.get_metrics', {}).body
        return {name: value for name, value, _ in metrics}
