from __future__ import print_function

import functools

import zmq


class ControlClient(object):
    def __init__(self, endpoint):
        context = zmq.Context.instance()
        self.socket = context.socket(zmq.REQ)
        self.socket.rcvtimeo = 500
        self.socket.connect(endpoint)

    def _call(self, func_name, *args, **kwargs):
        self.socket.send_pyobj((func_name, args, kwargs))
        ret, error = self.socket.recv_pyobj()
        if error:
            raise error

        return ret

    def __getattr__(self, name):
        return self.__dict__.setdefault(
            name, functools.partial(self._call, name),
        )
