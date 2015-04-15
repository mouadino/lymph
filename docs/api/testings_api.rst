.. currentmodule:: lymph.testing

Testings API
============

.. class:: RpcMockTestCase

  Base mixin test class that provice a highlevel interface for mocking remote rpc
  calls.

  .. attribute:: rpc_mock_calls

      A List of the called rpc functions.

  .. method:: setup_rpc_mocks(mocks)

      Setup RPC mocks by passing all mocked RPC function as a dictionary in the form
      ``{'<service_name>.<function_name>': <return_value>}``, in case
      ``<return_value>`` is an exception, call will raise the exception.

      .. code-block:: python

          class SomeTest(RpcMockTestCase):

              def setUp(self):
                  super().setUp()
                  self.setup_rpc_mocks({
                      'upper.upper': 'HELLO WORLD',
                      'upper.echo': TypeError('...')
                      ...
                  })

  .. method:: update_rpc_mock(func_name, new_value)

      Update a mock od an already mocked RPC function.

      .. code-block:: python

          class SomeTest(RpcMockTestCase):

              def setUp(self):
                  super().setUp()
                  self.setup_rpc_mocks({
                      'upper.upper': 'HELLO WORLD',
                      'upper.echo': 'hello world',
                  })

             def test_something(self):
                  self.update_rpc_mock('upper.upper', 'A NEW VALUE')
                  ...

  .. method:: assert_rpc_calls(*expected_calls)

     This method is a convenient way of asserting that rpc function calls were
     made in a particular way:

      .. code-block:: python

          class SomeTest(RpcMockTestCase):

              def setUp(self):
                  super().setUp()
                  self.setup_rpc_mocks({
                      'upper.upper': 'HELLO WORLD',
                      'upper.echo': 'hello world',
                  })

             def test_something(self):
                 ...

                 self.assert_rpc_calls(
                     mock.call('upper.upper', text='hello world')
                 )

     ``mock.call(..)`` can contain `PyHamcrest`_ matchers for better and less brittle
     tests.


.. class:: EventMockTestCase

  Base mixin test class that provice a highlevel interface for mocking events emitted.

  .. attribute:: events

      A List of the emitted events.

  .. method:: assert_events_emitted(*expected_emitted)

     This method is a convenient way of asserting that events were emitted:

      .. code-block:: python

          class SomeTest(EventMockTestCase):

             def test_something(self):
                 ...

                 self.assert_emitted_evemts(
                     mock.call('upper.uppercase_transform_finished', {'text': 'hello world'})
                 )


.. class:: RPCServiceTestCase

  Test class for testing a unique RPC interface.

  .. attribute:: service_class

    Interface class to test, this attribute is abstract and must supplied by
    child class.

  .. attribute:: service_config

    Configuration to pass to service when calling ``apply_config()``.

  .. attribute:: client

    Shortcut for getting default ``lymph.Proxy`` instance for the service under test.

  .. method:: get_proxy(**kwargs)

    Return a ``lymph.Proxy`` instance of the service under test.

  .. method:: request(*args, **kwargs)

    Low level method to send a request to service under tests return ``ReplyChannel``
    instance.

  .. method:: emit(*args, **kwargs)

    Emit an event.


.. class:: WebServiceTestCase

  Test class for testing a unique Web interface.

  .. attribute:: client

    Return a Werkzeug test client associated to web interface under test.


.. _PyHamcrest: https://pypi.python.org/pypi/PyHamcrest
