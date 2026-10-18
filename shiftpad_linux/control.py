"""Local, same-user control channel for the background monitor and tray UI."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Callable


def socket_path() -> Path:
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    return runtime / "shiftpad-linux.sock"


class ControlServer:
    def __init__(self, path: Path | None = None):
        self.path = path or socket_path()
        self.sock: socket.socket | None = None

    def __enter__(self) -> ControlServer:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path.unlink(missing_ok=True)  # The daemon holds the single-instance lock.
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.sock.bind(str(self.path))
            os.chmod(self.path, 0o600)
            self.sock.listen(8)
            self.sock.setblocking(False)
        except Exception:
            self.sock.close()
            self.path.unlink(missing_ok=True)
            raise
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        if self.sock:
            self.sock.close()
        self.path.unlink(missing_ok=True)

    def poll(self, handler: Callable[[str], dict[str, object]]) -> None:
        assert self.sock is not None
        try:
            connection, _ = self.sock.accept()
        except BlockingIOError:
            return
        with connection:
            connection.settimeout(1)
            try:
                command = connection.recv(1024).decode("utf-8").strip()
                if command not in {"status", "activate", "restore", "reload", "enable", "disable", "cancel"}:
                    response: dict[str, object] = {"ok": False, "error": "comando inválido"}
                else:
                    response = handler(command)
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}
            try:
                connection.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode())
            except OSError:
                pass


def request(command: str, path: Path | None = None, timeout: float = 20) -> dict[str, object]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(path or socket_path()))
        connection.sendall((command + "\n").encode())
        chunks = []
        while sum(map(len, chunks)) < 8192:
            chunk = connection.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
    response = json.loads(b"".join(chunks).decode())
    if not isinstance(response, dict):
        raise RuntimeError("resposta inválida do serviço")
    return response
