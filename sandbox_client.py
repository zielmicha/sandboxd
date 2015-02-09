import socket
import tarfile
import io
import json
import sys

class Sandbox(object):
    def __init__(self, path):
        self.path = path
        self._tarout = io.BytesIO()
        self.tar = tarfile.open(fileobj=self._tarout, mode='w')
        self.timeout = None
        self.allow_network = False

    def start(self):
        if type(self.path) is tuple:
            self.sock = socket.socket()
        else:
            self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(self.path)
        self.output = self.sock.makefile('r+', bufsize=0)
        options = {'timeout': self.timeout,
                   'allow_network': self.allow_network}
        self.output.write(json.dumps(options) + '\n')
        self.tar.close()
        self.output.write(self._tarout.getvalue())
        self.sock.shutdown(socket.SHUT_WR)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        addr = (sys.argv[1], int(sys.argv[2]))
    elif len(sys.argv) == 2:
        addr = sys.argv[1]
    else:
        addr = 'sock'
    box = Sandbox(addr)
    box.tar.add('example.sh', arcname='init')
    box.timeout = 3
    box.start()
    for line in box.output:
        print '[inferior]', line.rstrip()
