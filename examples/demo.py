from __future__ import print_function, unicode_literals

import gevent
import lymph
from lymph.core import trace


class Client(lymph.Interface):
    delay = .1

    echo = lymph.proxy('echo')

    def on_start(self):
        super(Client, self).on_start()
        gevent.spawn(self.loop)

    @lymph.event('uppercase_transform_finished')
    def on_uppercase(self, event):
        print(self.echo.echo(text="DONE"), event.body)

    def apply_config(self, config):
        self.delay = config.get('delay', .1)

    def loop(self):
        i = 0
        while True:
            gevent.sleep(self.delay)
            trace.set_id()
            try:
                result = self.echo.upper(text='foo_%s' % i)
            except Exception as ex:
                print('Failed with ', ex)
                continue
            print("result = %s" % result)
            i += 1
