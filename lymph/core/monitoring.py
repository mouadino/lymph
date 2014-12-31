import time
import resource
import gevent
import msgpack
import zmq.green as zmq


RUSAGE_ATTRS = (
    'utime', 'stime',
    'maxrss', 'ixrss', 'idrss', 'isrss',
    'minflt', 'majflt', 'nswap',
    'inblock', 'oublock',
    'msgsnd', 'msgrcv',
    'nsignals', 'nvcsw', 'nivcsw',
)


class Monitor(object):
    def __init__(self, container, monitor_endpoint='tcp://127.0.0.1:44044'):
        self.container = container
        self.stats = None
        ctx = zmq.Context.instance()
        self.socket = ctx.socket(zmq.PUB)
        self.socket.connect(monitor_endpoint)

    def start(self):
        self.loop_greenlet = gevent.spawn(self.loop)

    def stop(self):
        self.loop_greenlet.kill()

    def get_rusage_stats(self, ru, previous):
        stats = {}
        for attr in RUSAGE_ATTRS:
            ru_attr = 'ru_%s' % attr
            stats[attr] = getattr(ru, ru_attr) - getattr(previous, ru_attr)
        return stats

    def loop(self):
        last_stats = time.monotonic()
        last_rusage = resource.getrusage(resource.RUSAGE_SELF)
        while True:
            gevent.sleep(2)
            dt = time.monotonic() - last_stats
            self.stats = self.container.stats()
            ru = resource.getrusage(resource.RUSAGE_SELF)
            self.stats.update({
                'dt': dt,
                'time': time.time(),
                'rusage': self.get_rusage_stats(ru, last_rusage),
            })
            last_rusage = ru
            last_stats += dt
            self.socket.send_multipart([
                b'stats',
                msgpack.dumps(self.stats)])
