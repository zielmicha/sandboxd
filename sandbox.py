import userns
import tarfile
import io
import os
import signal

class Sandbox(userns.UserNS):
    def __init__(self, tardata, timeout=None, uid=999, gid=999,
                 setup_fds_fn=None):
        self.tardata = tardata
        self.timeout = timeout
        self.setup_fds_fn = setup_fds_fn
        super(Sandbox, self).__init__(uid, gid)

    def setup_fds(self):
        if self.timeout is not None:
            signal.signal(signal.SIGALRM, self.timed_out)
            signal.alarm(self.timeout)
        if self.setup_fds_fn:
            self.setup_fds_fn()

    def timed_out(self, *signal_args):
        self.kill()

    def user_code(self):
        self.check_assumptions()
        os.chdir('/home/user')
        file = tarfile.open(fileobj=io.BytesIO(self.tardata))
        file.extractall()
        os.execv('./init', ['./init'])

    def check_assumptions(self):
        assert os.getpid() == 1
        assert os.getuid() == 999
        assert os.getgid() == 999
        assert os.getgroups() == []

if __name__ == '__main__':
    out = io.BytesIO()
    tar = tarfile.open(fileobj=out, mode='w')
    tar.add("example.sh", arcname='init')
    tar.close()
    ns = Sandbox(out.getvalue(), timeout=3)
    ns.run()
