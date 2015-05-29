#!/usr/bin/env python2.7
# Copyright (c) 2013-2014 Michal Zielinski <michal@zielinscy.org.pl>
# Copyright (c) 2015 Husarion Sp. z o.o.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
                               allow_network=options.get('allow_network', False),
                               setup_fds_fn=setup_fds_fn)
        inst.run()


if __name__ == '__main__':
    if len(sys.argv) == 2:
        serv = ThreadingUnixServer(sys.argv[1], Handler)
        serv.serve_forever()
    else:
        port = int(sys.argv[2])
        SocketServer.ThreadingTCPServer.allow_reuse_address = True
        server = SocketServer.ThreadingTCPServer((sys.argv[1], port), Handler)
        server.allow_reuse_address = True
        server.serve_forever()
