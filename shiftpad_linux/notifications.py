"""Best-effort desktop notification for an upcoming TV switch."""

from __future__ import annotations

import logging
import math
import subprocess
from pathlib import Path

from .system import host_environment


LOG = logging.getLogger(__name__)
ICON = Path(__file__).resolve().parent / "assets" / "couchpad.svg"


class CountdownNotification:
    def __init__(self) -> None:
        self.notification_id: int | None = None
        self.last_second: int | None = None
        self.available = True

    def show(self, remaining: float, tv_output: str) -> None:
        if not self.available or remaining <= 0:
            return
        seconds = math.ceil(remaining)
        if seconds == self.last_second:
            return
        label = "segundo" if seconds == 1 else "segundos"
        if self._send(f"TV em {seconds} {label}",
                      f"Controle detectado. O CouchPad vai trocar para {tv_output}.", 1800):
            self.last_second = seconds

    def activated(self) -> None:
        if self.notification_id is not None:
            self._send("TV ativada", "A sessão de jogo está ativa na TV.", 3000)
        self.notification_id = None
        self.last_second = None

    def cancel(self) -> None:
        if self.notification_id is not None:
            try:
                subprocess.run(
                    ["gdbus", "call", "--session", "--dest", "org.freedesktop.Notifications",
                     "--object-path", "/org/freedesktop/Notifications", "--method",
                     "org.freedesktop.Notifications.CloseNotification", str(self.notification_id)],
                    capture_output=True, timeout=1, check=False, env=host_environment(),
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                LOG.debug("Não foi possível fechar a notificação: %s", exc)
        self.notification_id = None
        self.last_second = None

    def _send(self, title: str, body: str, lifetime_ms: int) -> bool:
        args = ["notify-send", "--app-name=CouchPad", f"--icon={ICON}",
                "--transient", f"--expire-time={lifetime_ms}", "--print-id"]
        if self.notification_id is not None:
            args.append(f"--replace-id={self.notification_id}")
        try:
            result = subprocess.run(args + [title, body], capture_output=True, text=True,
                                    timeout=1, check=False, env=host_environment())
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "notify-send falhou")
            self.notification_id = int(result.stdout.strip())
            return True
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            LOG.warning("Notificação de contagem indisponível: %s", exc)
            self.available = False
            self.notification_id = None
            return False
