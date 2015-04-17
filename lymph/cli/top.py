# -*- coding: utf-8 -*-
import pprint

from lymph.client import Client
from lymph.cli.base import Command


class TopCommand(Command):
    """
    Usage: lymph top

    Show services metrics

    {COMMON_OPTIONS}

    """

    short_description = 'Show services metrics.'

    def run(self):
        client = Client.from_config(self.config)
        services = client.container.discover()
        if services:
            for interface_name in sorted(services):
                interface_instances = client.container.lookup(interface_name)
                for instance in interface_instances:
                    print(instance.endpoint)
                    metrics = client.request(instance.endpoint, 'lymph.get_metrics', {}).body
                    pprint.pprint(metrics)
                    print('=' * 10)
