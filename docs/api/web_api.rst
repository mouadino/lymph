.. currentmodule:: lymph.web


Web API
========

.. class:: WebServiceInterface

    .. attribute:: application

        WSGI application instance that this interface is running

    .. attribute:: url_map

        A `werkzeug.routing.Map`_ instance that is used to map requests to
        request handlers. Typically given as a class attribute.


Web Configuration
==================

.. describe:: port

    Static port to listen to. If not supplied lymph will bind to a random port.

.. describe:: wsgi_pool_size

    Gevent HTTP server Greenlets pool size.
    Default: None, which means no limit.

.. describe:: middlewares

    List of WSGI middlewares to use. For a WSGI middleware to be compatible with
    lymph web it must follow the the following template.

    .. code-block:: python

        class CORSMiddleware(object):
            def __init__(self, application, *args, **kwargs):
                """First argument must be the a WSGI app."""

            def __call__(self, environ, start_response):
                """WSGI callable."""


    Example of configuring a CORS middleware:

    .. code-block:: yaml

        # instance.yml
        dependencies:
            cors:
              class: module:CORSMiddleware
              origin: http://deliveryhero.com
              methods:
                 - GET

        interfaces:
            web:
                class: web:JsonrpcGateway
                middlewares:
                  - cors


.. _werkzeug.routing.Map: http://werkzeug.pocoo.org/docs/0.10/routing/#maps-rules-and-adapters
