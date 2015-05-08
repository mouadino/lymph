# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import sys
import time
import collections
import traceback

from six import text_type

from lymph.client import Client
from lymph.cli.base import Command


class TopCommand(Command):
    """
    Usage: lymph top [--sorted=<column> | -s <column>] [options]

    Show services metrics

    Options:

      --sorted=<column>, -s <column>          Sort by a specific column.

    {COMMON_OPTIONS}

    """

    short_description = 'Show services metrics.'

    def run(self):
        sort_by = self.args.get("--sorted", None)
        with Debugger():
            table = Table([
                ('name', 15),
                ('endpoint', 25),
                ('greenlets.count', 20),
                ('gevent.active', 20)
            ], sort_by)

            with self.terminal.fullscreen():
                while True:
                    table.instances = self.get_instances()
                    table.display(self.terminal)
                    time.sleep(1)
                    print(self.terminal.clear, end='')

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


class Table(object):

    def __init__(self, headers, sort_by="-name"):
        self.headers = headers
        self._instances = []
        self.sort_by = sort_by

    @property
    def sort_by(self):
        return self._sort_by

    @sort_by.setter
    def sort_by(self, sort_by):
        if not sort_by.startswith(("-", "+")):
            sort_by = "-" + sort_by
        self._ascending = sort_by[0] == "+"
        self._sort_by = sort_by[1:]

    @property
    def instances(self):
        return self._instances

    @instances.setter
    def instances(self, instances):
        self._instances = sorted(instances, reverse=self._ascending, key=lambda instance: getattr(instance, self._sort_by))

    def display(self, terminal):
        for header, size in self.headers:
            if header == self._sort_by:
                header += " ▼" if self._ascending else " ▲"
            header = self._truncate(header, size)
            print(terminal.bold(header), end=' ')
        print()  # flush
        for instance in self._instances:
            print(' '.join(self._truncate(getattr(instance, name), size) for name, size in self.headers))
        print()  # flush

    @staticmethod
    def _truncate(name, size):
        name = text_type(name)
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
        if type not in (KeyboardInterrupt, SystemExit):
            traceback.print_exception(type, value, tb, file=sys.stdout)
