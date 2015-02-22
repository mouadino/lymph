# -*- coding: utf-8 -*-
from __future__ import division, unicode_literals

import gevent
import math
import os
import time
import logging

from lymph.utils import SampleWindow
from lymph.core import trace
from lymph.exceptions import Timeout

logger = logging.getLogger(__name__)

UNKNOWN = 'unknown'
RESPONSIVE = 'responsive'
UNRESPONSIVE = 'unresponsive'
CLOSED = 'closed'


class Connection(object):
    def __init__(self, server, endpoint, heartbeat_interval=1, timeout=1):
        self.server = server
        self.endpoint = endpoint
        self.timeout = timeout
        self.heartbeat_interval = heartbeat_interval

        now = time.monotonic()
        self.last_seen = 0
        self.last_message = now
        self.created_at = now
        self.heartbeat_samples = SampleWindow(100, factor=1000)
        self.explicit_heartbeat_count = 0
        self.status = UNKNOWN

        self.received_message_count = 0
        self.sent_message_count = 0

        self.pid = os.getpid()

        self.heartbeat_loop_greenlet = self.server.container.spawn(self.heartbeat_loop)

    def __str__(self):
        return "connection to=%s last_seen=%s" % (self.endpoint, self._dt())

    def _dt(self):
        return time.monotonic() - self.last_seen

    @property
    def phi(self):
        p = self.heartbeat_samples.p(self._dt())
        if p == 0:
            return float('inf')
        return -math.log10(p)

    def heartbeat_loop(self):
        trace.set_id()
        logger.debug('Starting connection hearbeat to %s', self.endpoint)
        while True:
            start = time.monotonic()
            channel = self.server.ping(self.endpoint)
            try:
                channel.get(timeout=self.heartbeat_interval)
            except Timeout:
                pass
            except Exception as ex:
                logger.error('Heartbeat failed: %s', ex)
            else:
                self.heartbeat_samples.add(time.monotonic() - start)
                self.explicit_heartbeat_count += 1
                self.last_seen = time.monotonic()
            self.update_status()
            self.log_stats()
            gevent.sleep(self.heartbeat_interval)

    def update_status(self):
        now = time.monotonic()
        if now - self.last_seen >= self.timeout:
            self.status = UNRESPONSIVE
        else:
            self.status = RESPONSIVE

    def log_stats(self):
        roundtrip_stats = 'window (mean rtt={mean:.1f} ms; stddev rtt={stddev:.1f})'.format(**self.heartbeat_samples.stats)
        roundtrip_total_stats = 'total (mean rtt={mean:.1f} ms; stddev rtt={stddev:.1f})'.format(**self.heartbeat_samples.total.stats)
        logger.debug("pid=%s; %s; %s; phi=%.3f; ping/s=%.2f; status=%s" % (
            self.pid,
            roundtrip_stats,
            roundtrip_total_stats,
            self.phi,
            self.explicit_heartbeat_count / max(1, time.monotonic() - self.created_at),
            self.status,
        ))

    def close(self):
        if self.status == CLOSED:
            return
        self.status = CLOSED
        self.heartbeat_loop_greenlet.kill()
        self.server.disconnect(self.endpoint)

    def on_recv(self, msg):
        if not msg.is_idle_chatter():
            self.last_message = time.monotonic()
        self.received_message_count += 1

    def on_send(self, msg):
        if not msg.is_idle_chatter():
            self.last_message = time.monotonic()
        self.sent_message_count += 1

    def is_alive(self):
        return self.status == RESPONSIVE

    def stats(self):
        return {
            'endpoint': self.endpoint,
            'rtt': self.heartbeat_samples.stats,
            'phi': self.phi,
            'status': self.status,
            'sent': self.sent_message_count,
            'received': self.received_message_count,
        }
