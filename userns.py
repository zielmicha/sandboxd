import os
import tempfile
import time
import struct
import threading
import subprocess
import socket
from subprocess import check_call, call

binds = ['/usr', '/bin', '/sbin',
         '/lib', '/lib32', '/lib32', '/lib64']

_unshare = _libc = None

def _init():
    global _unshare, _libc, ctypes
    import ctypes
    _unshare = ctypes.CDLL('./unshare.so')
    _libc = ctypes.CDLL('libc.so.6')

SLEEP_TIME = 0.03

def errwrap(name, *args):
    func = getattr(_unshare, name)
    result = func(*args)
    if result < 0:
        raise OSError(ctypes.get_errno(), 'call %s%r failed with %d' % (name, args, result))
    return result

class UserNS(object):
    def __init__(self, uid, nick=None):
        _init()
        if not (uid > 50):
            raise ValueError('uid must be > 50')
        self.uid = uid
        self.nick = nick or 'u%d' % uid

        self.running = False
        # acquired when
        self.lock = threading.Lock()

    def run(self):
        try:
            self._stage0()
        finally:
            print 'run finished'

    def _stage0(self):
        self._setup_dir()
        self.child_pid = os.fork()
        if self.child_pid == 0:
            self._close_fds([0, 1, 2])
            os.setsid()
            errwrap('unshare_net')
            self._stage1()
            os._exit(0)
        else:
            os.wait()

    def attach(self, cmd, **kwargs):
        wait_r, wait_w = os.pipe()
        self.attach_async(cmd, wait_w, **kwargs)
        byte = os.read(wait_r, 1)
        if byte == 'E':
            raise AttachError(cmd)

    def attach_async(self, cmd, wait_pipe, stdin=0, stdout=1, stderr=2):
        self._wait_for_init()
        passfd.sendfd(self._initout, stdin, '\0'.join(cmd))
        passfd.sendfd(self._initout, stdout, 'nic')
        passfd.sendfd(self._initout, stderr, 'nic')
        passfd.sendfd(self._initout, wait_pipe, 'nic')

    def _stage1(self):
        if errwrap('fork_unshare_pid') == 0:
            errwrap('unshare_ipc')
            errwrap('unshare_uts')
            errwrap('unshare_mount')
            self._stage2()
            os._exit(0)
        else:
            os.wait()
        self._cleanup()

    def _cleanup(self):
        try:
            os.rmdir(self.dir)
        except OSError:
            pass

    def _setup_dir(self):
        self.dir = tempfile.mkdtemp()
        print 'directory', self.dir

    def _stage2(self):
        self._setup_fs()
        errwrap('unshare_mount')
        self._setup_env()
        os.chroot(self.dir)
        os.chdir('/')
        os.setgid(100)
        os.setuid(999)
        self.user_code()

    def user_code(self):
        print 'hello from user code'
        call(['ls', '/'])

    def _setup_fs(self):
        mount('-t', 'tmpfs', 'none', target=self.dir)
        os.chmod(self.dir, 0o755)

        for bind in binds:
            if os.path.exists(bind):
                mount('--bind', bind, target=self.dir + '/' + bind)

        mount('-t', 'proc', 'procfs', target=self.dir + '/proc')

        os.mkdir(self.dir + '/dev')
        for dev in ['null', 'zero', 'tty', 'urandom']:
            check_call(['cp', '-a', '/dev/' + dev, self.dir + '/dev/' + dev])

        mount('-t', 'devpts', 'devptsfs', target=self.dir + '/dev/pts')
        check_call(['cp', '-a', '/dev/pts/ptmx', self.dir + '/dev/ptmx'])
        check_call(['chmod', '666', '/dev/pts/ptmx', self.dir + '/dev/ptmx'])

        self.setup_more_fs()

    def setup_more_fs(self):
        pass

    def _setup_env(self):
        for k in os.environ.keys():
            if k not in ['TERM']:
                del os.environ[k]

        os.environ.update(dict(
            PATH='/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin',
            HOME='/home/' + self.nick
        ))

    def _close_fds(self, without):
        up = max(without) + 1
        os.closerange(up, subprocess.MAXFD)
        for i in xrange(0, up):
            if i not in without:
                try:
                    os.close(i)
                except OSError:
                    pass

def dev_exists(name):
    return call('ip link show %s >/dev/null 2>&1' % name, shell=True) == 0

def mount(*args, **kwargs):
    assert len(kwargs) == 1
    target = kwargs['target']
    cmd = ['mount'] + list(args) + [target]
    if not os.path.exists(target):
        os.mkdir(target)
    check_call(cmd)

def get_ip(i):
    c = i % 256
    i /= 256
    b = i % 256
    i /= 256
    a = i % 256
    a = 128 + (a % 128)
    return '10.%d.%d.%d' % (a, b, c)

class error(Exception):
    pass

class AttachError(error):
    pass

if __name__ == '__main__':
    ns = UserNS(int(os.environ.get('NSUID', 1007)))
    ns.run()
