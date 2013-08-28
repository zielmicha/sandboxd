#!/usr/bin/env python2.7
import SocketServer
import socket
import os
import json
import sys

import sandbox

dev_null = open('/dev/null', 'r')

class ThreadingUnixServer(SocketServer.ThreadingMixIn, SocketServer.UnixStreamServer):
    def server_bind(self):
        if os.path.exists(self.server_address):
            os.remove(self.server_address)
        SocketServer.UnixStreamServer.server_bind(self)
        os.chmod(self.server_address, 0o777)

class Handler(SocketServer.StreamRequestHandler):
    def handle(self):
        options = json.loads(self.rfile.readline())
        tardata = self.rfile.read()

        def setup_fds_fn():
            os.dup2(dev_null.fileno(), 0)
            os.dup2(self.connection.fileno(), 1)
            os.dup2(self.connection.fileno(), 2)

        inst = sandbox.Sandbox(tardata,
                               timeout=options.get('timeout'),
                               setup_fds_fn=setup_fds_fn)
        inst.run()


if __name__ == '__main__':
    serv = ThreadingUnixServer(sys.argv[1], Handler)
    serv.serve_forever()
