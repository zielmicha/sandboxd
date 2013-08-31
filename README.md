sandboxd
==================

sandboxd uses Linux namespaces to create sandboxes for executing code.
Unlike most sandboxes, it supports all systems calls and spawning new processes - and makes sure that
spawned processes are dead after main finishes (using PID NS).

sandboxd listens on Unix socket:

```
# run these commands as as root
# not needed, but helps preventing collisions
groupadd --gid 999 sandboxd
useradd --uid 999 --gid sandboxd sandboxd
# start server
python sandbox_d.py /path_to_listen_on
```

Make sure to set appropriate unix permissions on socket, so unauthorized users won't be able
to access sandbox.

Protocol
------------------

sandboxd expects that first line in the incoming connection will contain JSON encoded options.
Currently the only supported option is `timeout` - after process runs for `timeout` seconds it
will be killed with SIGKILL.

```
{"timeout": 5.5}
```

After newline character, TAR archive data should follow. This archive will be unpacked to
directory `/home/user` (in chroot, won't affect host filesystem). Then `/home/user/init` will
be run, with stdout and stderr redirected to socket.

Example
---------------------

```
import sandbox_client

box = sandbox_client.Sandbox('/path_to_connect_to')
box.tar.add('example.sh', arcname='init')
box.timeout = 3
box.start()
for line in box.output:
    print '[inferior]', line.rstrip()
```
