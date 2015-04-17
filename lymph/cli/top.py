# -*- coding: utf-8 -*-
from __future__ import print_function
import time

from blessings import Terminal

from lymph.client import Client
from lymph.cli.base import Command


class Metrics(object):
    mapping = (('InterfaceName', 'interface_name'), ('Endpoint', 'endpoint'), ("GreenLCount", 'greenlets.count'), ('GeventActive', 'gevent.active'))

    def __init__(self, metrics):
        self.metrics = metrics

    def get(self):
        result = []
        for metric in self.metrics:
            new_metrics = {}
            for new, old in self.mapping:
                new_metrics[new] = metric[old]
            result.append(new_metrics)
        return result


class Table(object):

    def __init__(self, *headers):
        self.headers = headers
        self.rows = []

    def _truncate(self, name, size):
        name = str(name)
        if len(name) > size:
            return name[:size-2] + ".."
        return name.ljust(size)

    def display(self, terminal):
        for header, size in self.headers:
            header = self._truncate(header, size)
            print(terminal.bold(header), end=' ')
        print() # flush
        for columns in self.rows:
            print(' '.join([self._truncate(columns[name], size) for name, size in self.headers]))
        print() # flush


class TopCommand(Command):
    """
    Usage: lymph top

    Show services metrics

    {COMMON_OPTIONS}

    """

    short_description = 'Show services metrics.'

    def get_instrance_metrics(self, instance):
        metrics = self.client.request(instance.endpoint, 'lymph.get_metrics', {}).body
        return {metric[0]: metric[1] for metric in metrics}

    def get_metrics(self):
        self.client = Client.from_config(self.config)
        services = self.client.container.discover()
        metrics = []
        if services:
            for interface_name in sorted(services):
                interface_instances = self.client.container.lookup(interface_name)
                for instance in interface_instances:
                    metrics.append({"interface_name": interface_name, "endpoint": instance.endpoint})
                    metrics[-1].update(self.get_instrance_metrics(instance))
        return metrics

    def run(self):
        terminal = Terminal()
        table = Table(('InterfaceName', 15), ('Endpoint', 25), ("GreenLCount", 20), ('GeventActive', 20))

        with terminal.fullscreen():
            while True:
                metrics = self.get_metrics()
                table.rows = Metrics(metrics).get()
                table.display(terminal)
                time.sleep(1)
                print(terminal.clear, end='')
