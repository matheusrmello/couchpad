"""Open/close the packaged UI with disabled automation and isolated XDG paths."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    manifest = json.loads((ROOT / "dist/build-info.json").read_text())
    artifact = ROOT / f"dist/CouchPad-{manifest['version']}-x86_64.AppImage"
    with tempfile.TemporaryDirectory(prefix="couchpad-package-qa-") as directory:
        root = Path(directory)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        env = os.environ.copy()
        wayland = env.get("WAYLAND_DISPLAY", "")
        if wayland and not wayland.startswith("/"):
            env["WAYLAND_DISPLAY"] = str(Path(env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / wayland)
        env.update(XDG_CONFIG_HOME=str(root / "config"), XDG_STATE_HOME=str(root / "state"),
                   XDG_RUNTIME_DIR=str(runtime),
                   PULSE_SERVER=env.get("PULSE_SERVER", f"unix:/run/user/{os.getuid()}/pulse/native"))
        log_path = ROOT / ".build/packaged-session.log"
        with log_path.open("w") as log:
            process = subprocess.Popen([str(artifact), "--appimage-extract-and-run"],
                                       env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                status = None
                deadline = time.monotonic() + 25
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"Aplicativo encerrou: consulte {log_path}")
                    try:
                        with socket.socket(socket.AF_UNIX) as client:
                            client.settimeout(2)
                            client.connect(str(runtime / "shiftpad-linux.sock"))
                            client.sendall(b"status\n")
                            status = json.loads(client.recv(8192))
                        break
                    except (OSError, ValueError):
                        time.sleep(.25)
                assert status and status["ok"], "Monitor não iniciou"
                assert not status["enabled"] and not status["active"], status
                time.sleep(4)
                assert process.poll() is None, "Interface encerrou prematuramente"
                os.killpg(process.pid, signal.SIGTERM)
                # Extract-and-run has a runtime parent as well as the GTK child.
                assert process.wait(timeout=30) in (0, -signal.SIGTERM), "Encerramento falhou"
                deadline = time.monotonic() + 10
                while (runtime / "shiftpad-linux.sock").exists() and time.monotonic() < deadline:
                    time.sleep(.1)
                assert not (runtime / "shiftpad-linux.sock").exists(), "Monitor filho não encerrou"
                assert not (root / "state/shiftpad-linux/session.json").exists()
                print(json.dumps({"passed": True, "status": status,
                                  "scope": "packaged startup and graceful shutdown; automation disabled"}))
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=60)


if __name__ == "__main__":
    main()
