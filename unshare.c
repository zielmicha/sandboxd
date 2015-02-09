#define _GNU_SOURCE
#include <sched.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <signal.h>
#include <stdio.h>
#include <setjmp.h>
#include <sys/prctl.h>
#include <linux/prctl.h>
#include <linux/capability.h>
#include <errno.h>

int unshare_mount() {
  return unshare(CLONE_NEWNS);
}

jmp_buf unshare_buf;

#define STACK_SIZE (1024 * 1024)
static char child_stack[STACK_SIZE];

int child_func(void* argp) {
  longjmp(unshare_buf, 1);
}

int fork_unshare_pid() {
  /**
   * I don't like this. clone(2) should be able to accept
   * NULL as childFunc.
   * Not portable (to HP-something, manpage says) and not
   * thread-safe.
   */
  if (setjmp(unshare_buf) != 0) {
    return 0;
  } else {
    pid_t pid = 1;
    int result = clone(child_func,
                       child_stack + STACK_SIZE,
                       CLONE_NEWPID | CLONE_PARENT_SETTID | SIGCHLD, NULL, &pid);
    if(result >= 0)
      return (int)pid;
    else
      return result;
  }
}

int unshare_uts() {
  return unshare(CLONE_NEWUTS);
}

int unshare_ipc() {
  return unshare(CLONE_NEWIPC);
}

int unshare_net() {
  return unshare(CLONE_NEWNET);
}

int dropcaps() {
    unsigned long cap;
    int code;

    for (cap=0; cap <= 63; cap++) {
        code = prctl(PR_CAPBSET_DROP, cap, 0, 0, 0);
        if (code == -1 && errno != EINVAL) {
            return -1;
        }
    }

    // TODO: if(prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == -1) return -1;
    // But our production servers still use 3.2.0

    return 0;
}
