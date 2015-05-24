# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import re
import sys
import time
import collections
import traceback
import operator as op

import gevent
import six
import blessed
import hurry.filesize as sizing

from lymph.client import Client
from lymph.cli.base import Command
from lymph.utils import Undefined
from lymph.exceptions import Timeout


def redirect_traceback(func):
    # With blessed stderr is disable, this show traceback in stdout, ignoring
    # SystemExit.
    def _inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SystemExit:
            pass
        except Exception:
            traceback.print_exc(file=sys.stdout)
    return _inner


class _Prettifier(object):
    def __init__(self):
        self._callables = {}

    def __call__(self, name, value):
        try:
            func = self._callables[name]
        except KeyError:
            return value
        else:
            return func(value)

    def register(self, *names):
        def _inner(func):
            for name in names:
                self._callables[name] = func
            return func
        return _inner


prettify = _Prettifier()


@prettify.register('rusage.maxrss')
def format_memory_usage(value):
    """Prettify sizes.

    Example:
        >>> format_memory_usage('81673856')
        '77M'
    """
    return sizing.size(int(value))


class TopCommand(Command):
    """
    Usage: lymph top [--order=<column> | -o <column>] [--fqdn=<fqdn>] [--name=<name>] [--columns=<columns>] [-n <ninst>] [-i <interval>] [-t <timeout>] [options]

    Display and update sorted metrics about services.

    Options:

      --order=<column>, -o <column>           Order a specific column.
      --fqdn=<fqdn>                           Show only metrics comming from machine with given full qualified domain name.
      --name=<name>                           Show only metrics comming from service with given name.
      --columns=<columns>                     Columns to show.
      -n <ninsts>                             Only display up to <ninsts> instances.
      -i <interval>                           Set interval between polling metrics.
      -t <timeout>                            Lymph request timeout.

    {COMMON_OPTIONS}

    """

    short_description = 'Display and update sorted metrics about services.'
    default_columns = [
        ('name', 20),
        ('endpoint', 25),
        ('rusage.maxrss', 20),
        ('greenlets.count', 20),
        ('rpc', 20),
        ('exceptions', 20),
    ]

    def __init__(self, *args, **kwargs):
        super(TopCommand, self).__init__(*args, **kwargs)
        self.terminal = blessed.Terminal()
        self.table = Table(self.default_columns, prettify=prettify)
        self.current_command = UserCommand()
        self.poller = MetricsPoller(Client.from_config(self.config))

    @redirect_traceback
    def run(self):
        self._parse_args()
        self.poller.run()
        with self.terminal.fullscreen():
            self._top()

    def _parse_args(self):
        sort_by = self.args.get('--order')
        if sort_by:
            self.table.sort_by = sort_by

        fqdn = self.args.get('--fqdn')
        if fqdn:
            self.poller.fqdn = fqdn

        name = self.args.get('--name')
        if name:
            self.poller.name = name

        limit = self.args.get('-n')
        if limit:
            try:
                self.table.limit = int(limit) + 1
            except ValueError:
                raise SystemExit('-n must be integer')

        interval = self.args.get('-i')
        if interval:
            try:
                self.poller.interval = int(interval)
            except ValueError:
                raise SystemExit('-i must be integer')

        timeout = self.args.get('-t')
        if timeout:
            try:
                self.poller.timeout = int(timeout)
            except ValueError:
                raise SystemExit('-t must be integer')

        columns = self.args.get('--columns')
        if columns:
            # TODO: Maybe --columns <name>:<size>,... !?
            self.table.headers = [(name, 20) for name in columns.split(',') if name]

    def _top(self):
        while True:
            with self.terminal.location(0, 2):
                self.table.display(self.terminal)
            self.table.instances = self.poller.instances
            with self.terminal.location(0, 1):
                print(self.current_command.status, end='')
                sys.stdout.flush()  # We don't want a new line after command.
                self._on_user_input()
            time.sleep(.01)
            print(self.terminal.clear, end='')

    def _on_user_input(self):
        command = self.current_command.read(self.terminal)
        if command:
            if command is QUIT:
                raise SystemExit()
            elif command is HELP:
                self._help()
            else:
                # TODO: Currently we only support 'sort by'.
                try:
                    self.table.sort_by = command
                except ValueError:
                    self.current_command.error = 'invalid sort by: %s' % command

    def _help(self):
        t = self.terminal
        with t.fullscreen():
            print(t.underline('Command') + t.move_x(20) + t.underline('Description'))
            for name, cmd in UserCommand.allowed_commands.items():
                print(name + t.move_x(20) + cmd.help)
            with t.location(0, t.height - 1):
                print('Press any key to continue...', end='')
            sys.stdout.flush()
            key_pressed = False
            while not key_pressed:
                key_pressed = self.current_command.getch(t)

# Commands.
QUIT = object()
HELP = object()


class UserCommand(object):

    Command = collections.namedtuple('Command', 'prefix help')

    allowed_commands = {
        'o': Command('order', 'Set sort by column e.g. +name'),
        '?': Command('', 'Show this help message')
    }

    def __init__(self):
        self._name = ''
        self._buffer = ''
        self.error = ''

    @property
    def status(self):
        if self.error:
            return 'error: %s' % self.error
        return '%s: %s' % (self._name, self._buffer) if self._name else ''

    def read(self, terminal):
        char = self.getch(terminal)
        if not char:
            return
        if self._name:
            self.error = ''
            if char.name == 'KEY_ENTER':
                cmd = self._buffer
                self.clear()
                return cmd
            elif char.name == 'KEY_DELETE':
                self._buffer = self._buffer[:-1]
            elif char.name == 'KEY_ESCAPE':
                self.clear()
            else:
                self._buffer += char
        else:
            self.error = ''
            if char.name == 'KEY_ESCAPE':
                return QUIT
            if str(char) == '?':
                return HELP
            try:
                self._name = self.allowed_commands[str(char)].prefix
            except KeyError:
                pass

    def getch(self, terminal):
        with terminal.cbreak():
            return terminal.inkey(timeout=.1)

    def clear(self):
        self._name = ''
        self._buffer = ''


class Table(object):

    def __init__(self, headers, limit=None, prettify=lambda _, value: value, sort_by=None):
        self._prettify = prettify
        self._instances = {}
        self._metrics_received = False

        self.headers = headers
        self.limit = limit
        self.sort_by = sort_by or '-name'

    @property
    def sort_by(self):
        return self._sort_by

    @sort_by.setter
    def sort_by(self, sort_by):
        if not sort_by.startswith(("-", "+")):
            sort_by = "-" + sort_by
        order, column = sort_by[0], sort_by[1:]
        for header, _ in self.headers:
            if column == header:
                self._sort_by = header
                break
        else:
            raise ValueError('Unkown column %r' % column)
        self._ascending = order == "+"

    @property
    def instances(self):
        return sorted(self._instances.values(), reverse=self._ascending, key=op.methodcaller('get', self._sort_by, default=None))

    @instances.setter
    def instances(self, new_instances):
        self._metrics_received = True
        self._instances = new_instances

    def display(self, terminal):
        self._display_headers(terminal)
        self._display_metrics(terminal)

    def _display_headers(self, terminal):
        for header, size in self.headers:
            if header == self._sort_by:
                header += " ▼" if self._ascending else " ▲"
            header = self._truncate(header, size)
            print(terminal.bold(header), end=' ')
        print()  # flush

    def _display_metrics(self, terminal):
        for instance in self.instances[:self.limit]:
            values = []
            for name, size in self.headers:
                try:
                    value = instance.get(name)
                except KeyError:
                    # In case user supplied an unknown metric.
                    value = 'N/A'
                values.append((self._prettify(name, value), size))
            print(' '.join(self._truncate(value, size) for value, size in values))
        if not self.instances:
            if self._metrics_received:
                print('No metrics found')
            else:
                print('Fetching metrics ...')
        print()  # flush

    @staticmethod
    def _truncate(value, size):
        value = six.text_type(value)
        if len(value) > size:
            return value[:size - 2] + ".."
        return value.ljust(size)


class MetricsPoller(object):

    def __init__(self, client, timeout=1, interval=2, fqdn=None, name=None):
        self._client = client
        self._instances = {}

        self.timeout = timeout
        self.interval = interval
        self.fqdn = fqdn
        self.name = name
        self.running = True

    @property
    def instances(self):
        return self._instances

    def run(self, *_):
        greenlet = gevent.spawn(self._loop)
        # Respawn when greenlet die.
        greenlet.link_exception(self.run)
        greenlet.start()

    def _loop(self):
        while self.running:
            self._refresh_metrics()
            time.sleep(self.interval)

    def _refresh_metrics(self):
        services = self._client.container.discover()
        alive_endpoints = set()
        for interface_name in services:
            if self.name and interface_name != self.name:
                continue
            interface_instances = self._client.container.lookup(interface_name)
            for instance in interface_instances:
                if self.fqdn and instance.fqdn != self.fqdn:
                    continue
                metrics = self._get_instance_metrics(instance)
                if not metrics:
                    continue
                self._instances[instance.endpoint] = InstanceInfo(interface_name, instance.endpoint, metrics)
                alive_endpoints.add(instance.endpoint)
        for endpoint in self._instances:
            if endpoint not in alive_endpoints:
                self._instances.pop(endpoint, None)

    def _get_instance_metrics(self, instance):
        try:
            metrics = self._client.request(instance.endpoint, 'lymph.get_metrics', {}, timeout=self.timeout).body
        except Timeout:
            return
        return {name: value for name, value, _ in metrics}


class InstanceInfo(collections.namedtuple('InstanceInfo', 'name endpoint metrics')):

    def get(self, name, default=Undefined):
        try:
            return getattr(self, name)
        except AttributeError:
            try:
                return self.metrics[name]
            except KeyError:
                if default is not Undefined:
                    return default
                raise
