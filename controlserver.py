from __future__ import print_function

import select

import zmq


class ControlServer(object):
    def __init__(self, endpoint):
        context = zmq.Context.instance()
        self.socket = context.socket(zmq.REP)
        self.socket.bind(endpoint)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, select.POLLIN)

    def _invalid_func(self, *args, **kwargs):
        raise ValueError("Invalid function call")

    def _resolve_func(self, name):
        if name == "handle_requests" or name.startswith("_"):
            return self._invalid_func

        return getattr(self, name, self._invalid_func)

    def handle_requests(self, timeout=None):
        if self.poller.poll(timeout):
            while True:
                try:
                    request = self.socket.recv_pyobj(zmq.NOBLOCK)
                except zmq.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        break

                    raise

                try:
                    name, args, kwargs = request
                    result = self._resolve_func(name)(*args, **kwargs)
                    resp = result, None
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    resp = None, e

                self.socket.send_pyobj(resp)


if __name__ == "__main__":
    class TestServer(ControlServer):
        def normal(self, s):
            s = "Got " + s
            print(s)
            return s

        def exception(self, msg):
            print("exception:", msg)
            raise ValueError(msg)

    endpoint = "ipc:///tmp/zmqcontrolservertest.ipc"
    server = TestServer(endpoint)
    sock = zmq.Context.instance().socket(zmq.REQ)
    sock.connect(endpoint)
    sock.send_pyobj(("normal", ["hello world"], {}))
    server.handle_requests(100)
    server.handle_requests(100)
    print(sock.recv_pyobj(zmq.NOBLOCK))

    sock.send_pyobj(("exception", ["hello world"], {}))
    server.handle_requests(100)
    server.handle_requests(100)
    print(sock.recv_pyobj(zmq.NOBLOCK))
