.. currentmodule:: lymph.web


Web API
========

.. class:: WebServiceInterface

    .. attribute:: default_http_port = 4080

        If there's no port provided in the interface config, the http interface
        is bound to this port.

    .. attribute:: application

        WSGI application instance that this interface is running

    .. attribute:: url_map

        A `werkzeug.routing.Map`_ instance that is used to map requests to
        request handlers.


URL Routing
-----------

Lymph's WebServiceInterface use under the hood Werkzeug routing to do the dispatching e.g.

.. code-block::
    :caption: pkg/interface.py

    from lymph.web.interfaces import WebServiceInterface

    from werkzeug.routing import Map, Rule


    class HTTPService(lymph.WebServiceInterface):

        url_map = Map([
            Rule('/', endpoint='index'),
            Rule('/api/do', endpoint='handlers:APIHandler'),
        ])

        def index(self, request):
            ...


When dispatching the request, lymph's WebServiceInterface will dispatch by trying in this order:

1. If specified endpoint have a ``dispatch`` attribute, then call this latter (a.k.a duck typing).
2. If current interface have a attribute called with same name as Rule's endpoint.
3. Try to import the handler from current package.

As an example the first rule ``Rule('/', endpoint='index')`` will dispatch to ``HTTPService.index`` function and
the second rule ``Rule('/api/do', endpoint='handlers:APIHandler')`` will dispatch to ``APIHandler`` class under ``pkg/handlers.py``.

.. _werkzeug.routing.Map: http://werkzeug.pocoo.org/docs/0.10/routing/#maps-rules-and-adapters
