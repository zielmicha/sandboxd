import os
import tempfile
import time
import struct
import threading
import subprocess
import socket
import signal
import traceback
from subprocess import check_call, call

binds = ['/usr', '/bin', '/sbin',
         '/lib', '/lib32', '/lib32', '/lib64',
         '/opt']

_unshare = _libc = None

def _init():
    global _unshare, _libc, ctypes
    import ctypes
    _unshare = ctypes.CDLL('./unshare.so')
    _libc = ctypes.CDLL('libc.so.6')

def _kill_on_parent_exit():
    PR_SET_PDEATHSIG = 1
    _libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL)

SLEEP_TIME = 0.03

def errwrap(name, *args):
    func = getattr(_unshare, name)
    result = func(*args)
    if result < 0:
        raise OSError(ctypes.get_errno(), 'call %s%r failed with %d' % (name, args, result))
    return result

class UserNS(object):
    def __init__(self, uid, gid):
        _init()
        if not (uid > 50):
            raise ValueError('uid must be > 50')

        self._init_pid = None
        self.uid = uid
        self.gid = gid

    def run(self):
        try:
            self._stage0()
        finally:
            self._cleanup()

    def _stage0(self):
        self._setup_dir()
        self._init_pid_pipe()
        self.child_pid = os.fork()
        # fork_unshare_pid is not thread safe, so we need to fork
        if self.child_pid == 0:
            try:
                _kill_on_parent_exit()
                self.setup_fds()
                self._close_fds([0, 1, 2, self._pid_pipe[1]])
                os.setsid()
                errwrap('unshare_net')
                self._stage1()
            except:
                traceback.print_exc()
            finally:
                os._exit(0)
        else:
            self._read_pid()
            os.wait()

    def setup_fds(self):
        pass

    def _init_pid_pipe(self):
        a, b = os.pipe()
        self._pid_pipe = a, b

    def _read_pid(self):
        self._init_pid, = struct.unpack('!I', os.read(self._pid_pipe[0], 4))

    def _write_pid(self, pid):
        self._init_pid = pid
        os.write(self._pid_pipe[1], struct.pack('!I', pid))

    def _stage1(self):
        child_pid = errwrap('fork_unshare_pid')
        if child_pid == 0:
            # we are init in this namespace, so our death
            # should kill all children, thought it's not sure if it happens
            try:
                _kill_on_parent_exit()
                errwrap('unshare_ipc')
                errwrap('unshare_uts')
                errwrap('unshare_mount')
                self._stage2()
            except:
                traceback.print_exc()
            finally:
                os._exit(0)
        else:
            self._write_pid(child_pid)
            try:
                os.wait()
            except OSError:
                pass
        self._cleanup()

    def kill(self):
        if self._init_pid:
            os.kill(self._init_pid, signal.SIGKILL)
            self._cleanup()

    def _cleanup(self):
        try:
            os.rmdir(self.dir)
        except OSError:
            pass

    def _setup_dir(self):
        self.dir = tempfile.mkdtemp()

    def _stage2(self):
        self._setup_fs()
        errwrap('unshare_mount')
        self._setup_env()
        os.chroot(self.dir)
        os.chdir('/')
        os.setgroups([])
        os.setgid(self.gid)
        os.setuid(self.uid)
        self.user_code()

    def user_code(self):
        # overwrite this
        print 'hello from user code'

    def _setup_fs(self):
        mount('-t', 'tmpfs', 'none', target=self.dir)
        os.chmod(self.dir, 0o755)

        for bind in binds:
            if os.path.exists(bind):
                mount('--bind', bind, target=self.dir + '/' + bind)

        mount('-t', 'proc', 'procfs', target=self.dir + '/proc')

        dev_null = open('/dev/null', 'w')
        os.mkdir(self.dir + '/dev')
        for dev in ['null', 'zero', 'tty', 'urandom']:
             try:
                 check_call(['cp', '-a', '/dev/' + dev, self.dir + '/dev/' + dev], stderr=dev_null)
             except subprocess.CalledProcessError:
                 # doesn't require CAP_SYS_ADMIN
                 check_call(['touch', self.dir + '/dev/' + dev])
                 check_call(['mount', '--bind', '/dev/' + dev, self.dir + '/dev/' + dev])

        mount('--bind', '/dev/pts', target=self.dir + '/dev/pts')
        try:
             check_call(['cp', '-a', '/dev/pts/ptmx', self.dir + '/dev/ptmx'], stderr=dev_null)
        except subprocess.CalledProcessError:
             check_call(['ln', '-s', '/dev/pts/ptmx', self.dir + '/dev/ptmx'])
        check_call(['chmod', '666', '/dev/pts/ptmx', self.dir + '/dev/ptmx'])

        os.makedirs(self.dir + '/home/user')
        os.chown(self.dir + '/home/user', self.uid, self.gid)

    def _setup_env(self):
        for k in os.environ.keys():
            if k not in ['TERM']:
                del os.environ[k]

        os.environ.update(dict(
            PATH='/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin',
            HOME='/home/user',
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

def mount(*args, **kwargs):
    assert len(kwargs) == 1
    target = kwargs['target']
    cmd = ['mount'] + list(args) + [target]
    if not os.path.exists(target):
        os.mkdir(target)
    check_call(cmd)

class error(Exception):
    pass

if __name__ == '__main__':
    ns = UserNS(999, 999)
    ns.run()
