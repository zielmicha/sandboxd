import userns
import tarfile
import io
import os
import signal

class Sandbox(userns.UserNS):
    def __init__(self, tardata, timeout=None, uid=999, gid=999):
        self.tardata = tardata
        self.timeout = timeout
        super(Sandbox, self).__init__(uid, gid)

    def setup_fds(self):
        if self.timeout is not None:
            signal.signal(signal.SIGALRM, self.timed_out)
            signal.alarm(self.timeout)

    def timed_out(self, *signal_args):
        self.kill()

    def user_code(self):
        os.chdir('/home/user')
        file = tarfile.open(fileobj=io.BytesIO(self.tardata))
        file.extractall()
        os.execv('./init', ['./init'])

if __name__ == '__main__':
    out = io.BytesIO()
    tar = tarfile.open(fileobj=out, mode='w')
    tar.add("example.sh", arcname='init')
    tar.close()
    ns = Sandbox(out.getvalue(), timeout=3)
    ns.run()
