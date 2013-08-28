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

    def start(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(self.path)
        self.output = self.sock.makefile('r+', bufsize=0)
        options = {'timeout': self.timeout}
        self.output.write(json.dumps(options) + '\n')
        self.tar.close()
        self.output.write(self._tarout.getvalue())
        self.sock.shutdown(socket.SHUT_WR)

if __name__ == '__main__':
    box = Sandbox(sys.argv[1] if sys.argv[1:] else 'sock')
    box.tar.add('example.sh', arcname='init')
    box.timeout = 3
    box.start()
    for line in box.output:
        print '[inferior]', line.rstrip()
