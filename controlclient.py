from __future__ import print_function

import functools

import zmq


class ControlClient(object):
    def __init__(self, endpoint, resp_timeout=500):
        context = zmq.Context.instance()
        self.socket = context.socket(zmq.REQ)
        self.fire_and_forget = resp_timeout < 0
        if not self.fire_and_forget:
            self.socket.rcvtimeo = resp_timeout

        self.socket.connect(endpoint)

    def _call(self, func_name, *args, **kwargs):
        self.socket.send_pyobj((func_name, args, kwargs))
        if self.fire_and_forget:
            return

        ret, error = self.socket.recv_pyobj()
        if error:
            raise error

        return ret

    def __getattr__(self, name):
        return self.__dict__.setdefault(
            name, functools.partial(self._call, name),
        )
