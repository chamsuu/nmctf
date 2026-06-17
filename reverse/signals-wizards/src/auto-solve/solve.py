#!/usr/bin/env python3
"""
Signal Wizard CTF Challenge Solver

The challenge is timing-sensitive: signals sent before a stage installs its
handler are lost or kill the process. This solver reads the program output and
only sends each signal after the matching stage is ready.
"""

"""
it can be solved manualy without any scripting
"""
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
FLAG_RE = re.compile(r"FLAG:\s*([^\r\n]+)")


WAITPID_SHIM = r"""
#define _GNU_SOURCE
#include <errno.h>
#include <sys/types.h>
#include <sys/wait.h>

pid_t waitpid(pid_t pid, int *status, int options) {
    if (pid == -1 && (options & WNOHANG)) {
        if (status) {
            *status = 42 << 8;
        }
        return 4242;
    }

    errno = ECHILD;
    return -1;
}
"""


class OutputReader:
    def __init__(self, stream):
        self._stream = stream
        self._buf = []
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def _read(self):
        while True:
            chunk = self._stream.read(1)
            if chunk == "":
                self._queue.put(None)
                return
            self._queue.put(chunk)

    def _drain(self):
        while True:
            try:
                chunk = self._queue.get_nowait()
            except queue.Empty:
                return
            if chunk is None:
                return
            self._buf.append(chunk)

    @property
    def text(self):
        self._drain()
        return "".join(self._buf)

    def wait_for(self, needle, timeout=15.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if needle in self.text:
                return
            time.sleep(0.02)
        raise TimeoutError(f"timed out waiting for output: {needle!r}")


def build_waitpid_shim():
    gcc = shutil.which("gcc")
    if gcc is None:
        raise RuntimeError("gcc is required to build the stage-4 waitpid shim")

    tmpdir = tempfile.mkdtemp(prefix="signal_wizard_solve_")
    src = os.path.join(tmpdir, "waitpid_shim.c")
    so = os.path.join(tmpdir, "waitpid_shim.so")

    with open(src, "w", encoding="ascii") as f:
        f.write(textwrap.dedent(WAITPID_SHIM).strip() + "\n")

    result = subprocess.run(
        [gcc, "-shared", "-fPIC", "-O2", "-o", so, src],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"failed to build waitpid shim:\n{result.stderr}")

    return tmpdir, so


def send(pid, sig, delay=0.25):
    os.kill(pid, sig)
    time.sleep(delay)


def solve_all_stages(binary_path=None):
    if binary_path is None:
        binary_path = "./signal_wizard"

    binary_path = os.path.abspath(binary_path)
    if not os.path.exists(binary_path):
        print(f"Error: {binary_path} not found")
        return False

    print("[*] Starting Signal Wizard solver...")
    shim_dir = None
    proc = None

    try:
        shim_dir, shim_path = build_waitpid_shim()
        env = os.environ.copy()
        env["LD_PRELOAD"] = shim_path

        proc = subprocess.Popen(
            [binary_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=0,
            env=env,
        )
        out = OutputReader(proc.stdout)
        pid = proc.pid
        print(f"[*] Challenge PID: {pid}")

        out.wait_for("Press Enter to begin", timeout=15)
        proc.stdin.write("\n")
        proc.stdin.flush()

        print("[*] Stage 1: sending SIGINT 3 times")
        out.wait_for("ready for SIGINT", timeout=15)
        for _ in range(3):
            send(pid, signal.SIGINT, 0.2)

        print("[*] Stage 2: sending SIGUSR1 then SIGUSR2")
        out.wait_for("THE ORDERED ORACLE", timeout=15)
        out.wait_for("[*] Waiting:", timeout=15)
        send(pid, signal.SIGUSR1, 0.2)
        send(pid, signal.SIGUSR2, 0.2)

        print("[*] Stage 3: sending SIGALRM")
        out.wait_for("THE ALARM WRAITH", timeout=15)
        out.wait_for("Time left:", timeout=15)
        send(pid, signal.SIGALRM, 0.2)

        print("[*] Stage 4: sending SIGCHLD with waitpid shim active")
        out.wait_for("THE CHILD SPECTER", timeout=15)
        time.sleep(0.2)
        send(pid, signal.SIGCHLD, 0.2)

        print("[*] Stage 5: sending SIGSEGV")
        out.wait_for("THE STACK PHANTOM", timeout=15)
        time.sleep(0.2)
        send(pid, signal.SIGSEGV, 0.2)

        print("[*] Stage 6: reading /proc and sending SIGTSTP")
        out.wait_for("THE PROC NECROMANCER", timeout=15)
        with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as f:
            print(f"    [+] /proc/{pid}/comm: {f.read().strip()}")
        with open(f"/proc/{pid}/status", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS"):
                    print(f"    [+] {line.strip()}")
                    break
        time.sleep(0.2)
        send(pid, signal.SIGTSTP, 0.2)

        print("[*] Stage 7: sending SIGUSR1 3 times, then SIGINT")
        out.wait_for("THE GRAND SIGNAL ARCHMAGE", timeout=15)
        out.wait_for("SIGUSR1 received: 0/3", timeout=15)
        for _ in range(3):
            send(pid, signal.SIGUSR1, 0.2)
        send(pid, signal.SIGINT, 0.2)

        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise RuntimeError("challenge did not exit after the final stage")

        stdout = out.text
        clean_stdout = ANSI_RE.sub("", stdout)
        stderr = proc.stderr.read()
        if stderr:
            print("[!] Stderr:")
            print(stderr)

        match = FLAG_RE.search(clean_stdout)
        flag = match.group(1).strip() if match else ""
        if not flag:
            print("\n[!] Challenge output:")
            print(clean_stdout)
            raise RuntimeError("solver finished but no flag was printed")

        print(f"\n[+] Flag: {flag}")
        return True

    except Exception as e:
        print(f"[!] Error: {e}")
        if proc and proc.poll() is None:
            proc.kill()
            proc.wait()
        return False
    finally:
        if shim_dir:
            shutil.rmtree(shim_dir, ignore_errors=True)


if __name__ == "__main__":
    binary = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(0 if solve_all_stages(binary) else 1)
