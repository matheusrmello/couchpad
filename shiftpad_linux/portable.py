"""Desktop entry point for the self-contained AppImage beta."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from . import __version__, displays
from .config import config_path
from .control import request


LOG = logging.getLogger(__name__)
_monitor: subprocess.Popen | None = None


def ensure_configuration() -> bool:
    """Create a disabled, machine-independent profile on the first launch."""
    path = config_path()
    if path.exists():
        return False
    snapshot = displays.capture()
    connected = [item for item in snapshot["outputs"] if item.get("connected")]
    if not connected:
        raise RuntimeError("Nenhum monitor conectado foi identificado pelo KScreen")
    desktop = next((item for item in connected if item.get("enabled")), connected[0])
    target = next((item for item in connected if item["name"] != desktop["name"]), None)
    tv = target["name"] if target else "TV-NOT-CONFIGURED"
    digest = displays.edid_sha256(tv) if target else ""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    text = (
        '# CouchPad beta: selecione os dispositivos antes de ativar.\n'
        '[general]\nenabled = false\n\n'
        '[display]\n'
        f'desktop_output = {json.dumps(desktop["name"])}\n'
        f'tv_output = {json.dumps(tv)}\n'
        f'tv_edid_sha256 = {json.dumps(digest or "")}\n'
        'mode = "tv-only"\n\n'
        '[audio]\ntv_sink = ""\n\n'
        '[gamepad]\nname_contains = ""\nvendor_id = ""\nproduct_id = ""\nuniq = ""\n'
        'activation_buttons = []\nconnect_delay = 2\ndisconnect_delay = 2\n\n'
        '[launcher]\nstart = []\nstop = []\ncustom_path = ""\n'
        'custom_enabled = false\ncustom_close = false\ncustom_args = []\n\n'
        '[cec]\non = []\noff = []\n'
    )
    try:
        with path.open("x", encoding="utf-8") as file:
            path.chmod(0o600)
            file.write(text)
    except FileExistsError:
        return False
    return True


def monitor_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "run"]
    return [sys.executable, "-m", "shiftpad_linux", "run"]


def ensure_monitor(timeout: float = 12) -> bool:
    """Reuse a running daemon, or own a child for the lifetime of this GUI."""
    global _monitor
    try:
        state = request("status", timeout=2)
        if state.get("ok"):
            return _monitor is not None and _monitor.poll() is None
    except (OSError, ValueError, RuntimeError):
        pass
    if _monitor is not None and _monitor.poll() is None:
        raise RuntimeError("O monitor está ocupado; tente novamente em alguns segundos")
    _monitor = subprocess.Popen(monitor_command())
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _monitor.poll() is not None:
            # Another launcher may have acquired the daemon lock first.
            try:
                if request("status", timeout=1).get("ok"):
                    _monitor = None
                    return False
            except (OSError, ValueError, RuntimeError):
                pass
            raise RuntimeError("O monitor automático não iniciou; consulte o diagnóstico")
        try:
            if request("status", timeout=1).get("ok"):
                os.environ["COUCHPAD_OWNS_MONITOR"] = "1"
                return True
        except (OSError, ValueError, RuntimeError):
            pass
        time.sleep(0.1)
    stop_monitor()
    raise RuntimeError("O monitor automático demorou demais para iniciar")


def stop_monitor() -> None:
    global _monitor
    if _monitor is not None and _monitor.poll() is None:
        _monitor.terminate()
        try:
            _monitor.wait(timeout=60)
        except subprocess.TimeoutExpired:
            # Keep the process and AppImage mounted: SIGKILL could interrupt
            # desktop recovery. Let the user diagnose rather than lose state.
            LOG.error("Aguardando o monitor concluir a restauração do desktop")
            _monitor.wait()
    _monitor = None


def runtime_check() -> int:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf, Gtk
    import cairo
    import evdev
    assets = Path(__file__).resolve().parent / "assets"
    for asset in assets.glob("*.svg"):
        GdkPixbuf.Pixbuf.new_from_file_at_scale(str(asset), 24, 24, True)
    print(json.dumps({"version": __version__, "frozen": bool(getattr(sys, "frozen", False)),
                      "gtk": f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}",
                      "assets": len(list(assets.glob("*.svg"))),
                      "evdev": bool(evdev.InputDevice), "cairo": cairo.cairo_version_string()},
                     ensure_ascii=False))
    return 0


def show_error(message: str) -> None:
    print(f"CouchPad beta: {message}", file=sys.stderr)
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        ready, _ = Gtk.init_check(None)
        if ready:
            dialog = Gtk.MessageDialog(
                message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                text="Não foi possível iniciar o CouchPad beta",
            )
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()
    except Exception:
        LOG.exception("Não foi possível mostrar a mensagem gráfica")


def main() -> int:
    from .cli import main as cli_main
    if sys.argv[1:] == ["--runtime-check"]:
        return runtime_check()
    if len(sys.argv) > 1:
        return cli_main(sys.argv[1:])
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        missing = [name for name in ("kscreen-doctor", "pactl") if not shutil.which(name)]
        if missing:
            raise RuntimeError("Esta beta requer KDE Plasma e as ferramentas: " + ", ".join(missing))
        ensure_configuration()
        owned = ensure_monitor()
        os.environ["COUCHPAD_OWNS_MONITOR"] = "1" if owned else "0"
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib, Gtk
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, lambda *_: GLib.idle_add(Gtk.main_quit))
        from .tray import main as tray_main
        tray_main()
        return 0
    except Exception as exc:
        LOG.exception("Falha na inicialização da beta")
        show_error(str(exc))
        return 1
    finally:
        stop_monitor()
