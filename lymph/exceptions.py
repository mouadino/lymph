
class RpcError(Exception):
    def __init__(self, msg, *args, **kwargs):
        self.message = msg or ''
        super(RpcError, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.message

    __repr__ = __str__


class Timeout(RpcError):
    pass


class Nack(RpcError):
    pass


class LookupFailure(RpcError):
    pass


class RegistrationFailure(Exception):
    pass


class ErrorReply(RpcError):
    def __init__(self, request, reply, *args, **kwargs):
        self.request = request
        self.reply = reply

        try:
            message = '{type}: {message}'.format(**reply.body)
        except KeyError:
            message = str(reply.body)
        super(ErrorReply, self).__init__(message, *args, **kwargs)


class SocketNotCreated(Exception):
    pass


class NotConnected(Exception):
    pass
