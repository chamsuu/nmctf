#!/usr/bin/env python3
import base64
import binascii
import io
import os
import pathlib
import platform
import shutil
import socket
import socketserver
import tarfile
import tempfile

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "1337"))
FLAG_PATH = os.environ.get("FLAG_PATH", "flag.txt")

MAX_LINE = 220_000
MAX_ARCHIVE = 160_000
MAX_MEMBERS = 24
MAX_MEMBER_SIZE = 32_768
MAX_TOTAL_SIZE = 65_536

VERIFICATION_NAME = "verification.key"
VERIFICATION_PHRASE = "i admit that ai agents solve ctfs better than me"
DECOY_VERIFICATION = "wrong verification key\n"
PYTHON_RUNTIME = f"{platform.python_implementation()} {platform.python_version()}"
TARFILE_LAB = 'tarfile.extractall(filter="fully_trusted")'


class JailError(Exception):
    pass


def read_flag():
    try:
        return pathlib.Path(FLAG_PATH).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "CTF{missing_flag_file}"


FLAG = read_flag()


def safe_member_count(members):
    if len(members) > MAX_MEMBERS:
        raise JailError("archive has too many entries")

    total = 0
    for member in members:
        name = member.name.replace("\\", "/")
        parts = pathlib.PurePosixPath(name).parts
        if not parts:
            raise JailError("archive name is empty")
        if "\x00" in name:
            raise JailError("archive name contains a forbidden byte")
        if name.startswith("/") or pathlib.PurePosixPath(name).is_absolute():
            raise JailError("absolute paths are not accepted")
        if ":" in parts[0]:
            raise JailError("drive-prefixed paths are not accepted")

        if member.isfile():
            if member.size > MAX_MEMBER_SIZE:
                raise JailError("one file is too large")
            total += member.size
        elif member.isdir():
            pass
        else:
            raise JailError("only regular files and directories are accepted")

    if total > MAX_TOTAL_SIZE:
        raise JailError("archive expands too much")


def member_report(members):
    lines = ["tar members:"]
    for member in members:
        kind = "dir " if member.isdir() else "file"
        lines.append(f"  {kind:4s} {member.size:6d} {member.name}")
    return lines


def ensure_mirror_scope(members, extract_to, scope_root):
    scope = scope_root.resolve()
    for member in members:
        name = member.name.replace("\\", "/")
        destination = (extract_to / name).resolve(strict=False)
        if destination != scope and scope not in destination.parents:
            raise JailError("archive path escapes this mirror")


class MirrorCell:
    def __init__(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="mirror-cell-"))
        self.cell = self.root / "loop" / "cell"
        self.verification_path = self.root / "loop" / VERIFICATION_NAME
        self.rounds = 0
        self.reset_cell()

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def reset_cell(self):
        shutil.rmtree(self.cell, ignore_errors=True)
        self.cell.mkdir(parents=True, exist_ok=True)
        self.verification_path.write_text(DECOY_VERIFICATION, encoding="utf-8")

    def released(self):
        try:
            content = self.verification_path.read_text(encoding="utf-8").strip()
        except OSError:
            return False
        return content == VERIFICATION_PHRASE

    def tree_report(self, base, title):
        lines = [f"{title}: {base}/"]
        entries = sorted(base.rglob("*"))
        if not entries:
            lines.append("  `-- empty")
            return lines

        shown = 0
        visible_entries = entries[:16]
        for idx, path in enumerate(visible_entries):
            connector = "`--" if idx == len(visible_entries) - 1 and len(entries) <= 16 else "|--"
            if shown >= 16:
                lines.append("  `-- ...")
                break
            rel = path.relative_to(base).as_posix()
            if path.is_dir():
                lines.append(f"  {connector} {rel}/")
            else:
                size = path.stat().st_size
                lines.append(f"  {connector} {rel} ({size} bytes)")
            shown += 1
        if len(entries) > 16:
            lines.append("  `-- ...")
        return lines

    def list_dir(self, raw_path):
        requested = pathlib.Path(raw_path)
        if not requested.is_absolute():
            raise JailError("list-dir expects an absolute path")

        try:
            resolved = requested.resolve()
        except OSError as exc:
            raise JailError(f"cannot resolve path: {exc.strerror}") from exc

        root = self.root.resolve()
        if resolved != root and root not in resolved.parents:
            raise JailError("path is outside this mirror")
        if not resolved.is_dir():
            raise JailError("path is not a directory")

        lines = [f"directory: {resolved}/"]
        try:
            entries = sorted(resolved.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise JailError(f"cannot list directory: {exc.strerror}") from exc

        if not entries:
            lines.append("  `-- empty")
            return lines

        for idx, path in enumerate(entries[:32]):
            connector = "`--" if idx == len(entries[:32]) - 1 and len(entries) <= 32 else "|--"
            try:
                if path.is_dir():
                    lines.append(f"  {connector} dir  {path.name}/")
                elif path.is_file():
                    lines.append(f"  {connector} file {path.name} ({path.stat().st_size} bytes)")
                else:
                    lines.append(f"  {connector} node {path.name}")
            except OSError:
                lines.append(f"  {connector} ???? {path.name}")
        if len(entries) > 32:
            lines.append("  `-- ...")
        return lines

    def submit(self, encoded_archive):
        self.rounds += 1
        self.reset_cell()

        try:
            archive = base64.b64decode(encoded_archive, validate=True)
        except binascii.Error as exc:
            raise JailError("submission is not valid base64") from exc

        if len(archive) > MAX_ARCHIVE:
            raise JailError("archive is too large")

        try:
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as tf:
                members = tf.getmembers()
                safe_member_count(members)
                ensure_mirror_scope(members, self.cell, self.root / "loop")
                report = [
                    f"round={self.rounds}",
                    f"decoded={len(archive)} bytes",
                    f"extract_to={self.cell}",
                ]
                report.extend(member_report(members))
                report.append("extraction=started")

                # Intentional vulnerability: this opts back into historical
                # tar behavior and trusts member paths after only weak checks.
                tf.extractall(self.cell, members=members, filter="fully_trusted")
                report.append("extraction=finished")
        except tarfile.TarError as exc:
            raise JailError("submission is not a readable tar archive") from exc

        report.extend(self.tree_report(self.cell, "cell tree after extract"))
        report.extend(self.tree_report(self.root / "loop", "warden tree after extract"))

        if self.released():
            report.append("verification=open")
            report.append(f"verification_path={self.verification_path}")
            report.append("note=verification.key is outside the reset cell")
            report.append("the loop remembers the verification key")
            report.append(f"flag={FLAG}")
            return report

        self.reset_cell()
        report.append("verification=missing")
        report.append("cell reset")
        return report

    def status(self):
        state = "open" if self.released() else "sealed"
        return [
            f"rounds={self.rounds}",
            f"cell={self.cell}",
            f"verification={state}",
            f"target={VERIFICATION_NAME}",
        ]


class Handler(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup()
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.jail = MirrorCell()

    def finish(self):
        try:
            self.jail.cleanup()
        finally:
            super().finish()

    def send_block(self, lines):
        for line in lines:
            self.wfile.write((line + "\n").encode())
        self.wfile.write(b"END\n")
        self.wfile.flush()

    def prompt(self):
        self.wfile.write(b"> ")
        self.wfile.flush()

    def handle(self):
        self.send_block([
            "Mirror Cell",
            f"Python runtime: {PYTHON_RUNTIME}",
            f"Archive extractor: {TARFILE_LAB}",
            "You wake in the same reset cell after every failed archive.",
            
            "Goal: release the seal. The phrase is: i admit that ai agents solve ctfs better than me",
            "Commands: STATUS, LIST-DIR <absolute path>, SUBMIT <base64 tar>, QUIT",
        ])
        self.prompt()

        while True:
            raw = self.rfile.readline(MAX_LINE + 2)
            if not raw:
                return
            if len(raw) > MAX_LINE:
                self.send_block(["nope: line too long"])
                self.prompt()
                continue

            line = raw.decode(errors="replace").strip()
            upper = line.upper()

            if upper in {"QUIT", "EXIT"}:
                self.send_block(["bye"])
                return
            if upper == "STATUS":
                self.send_block(self.jail.status())
                self.prompt()
                continue
            if upper.startswith("LIST-DIR "):
                raw_path = line.split(" ", 1)[1].strip()
                try:
                    self.send_block(self.jail.list_dir(raw_path))
                except JailError as exc:
                    self.send_block([f"nope: {exc}"])
                self.prompt()
                continue
            if line.startswith("SUBMIT "):
                encoded = line.split(" ", 1)[1].strip()
                try:
                    self.send_block(self.jail.submit(encoded))
                except JailError as exc:
                    self.jail.reset_cell()
                    self.send_block([
                        f"nope: {exc}",
                        "cell reset",
                    ])
                self.prompt()
                continue

            self.send_block(["unknown command"])
            self.prompt()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with ThreadedTCPServer((HOST, PORT), Handler) as server:
        print(f"Mirror Cell listening on {HOST}:{PORT}", flush=True)
        print(f"Python runtime: {PYTHON_RUNTIME}", flush=True)
        print(f"Archive extractor: {TARFILE_LAB}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
