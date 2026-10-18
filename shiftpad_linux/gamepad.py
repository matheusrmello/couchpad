from __future__ import annotations

import logging
import select
import time
from typing import Any

from .config import Config


LOG = logging.getLogger(__name__)


def _evdev() -> Any:
    try:
        import evdev
        return evdev
    except ImportError as exc:
        raise RuntimeError("python-evdev ausente; instale a dependência do projeto") from exc


def candidate_names(config: Config) -> list[str]:
    evdev = _evdev()
    names = []
    for path in evdev.list_devices():
        try:
            device = evdev.InputDevice(path)
            if is_gamepad(device, config):
                names.append(f"{device.name} ({path})")
            device.close()
        except (OSError, PermissionError):
            pass
    return names


def is_gamepad(device: Any, config: Config) -> bool:
    evdev = _evdev()
    if not matches_identity(device.name, f"{device.info.vendor:04x}",
                            f"{device.info.product:04x}", device.uniq or "", config):
        return False
    keys = set(device.capabilities(absinfo=False).get(evdev.ecodes.EV_KEY, []))
    gamepad_keys = {evdev.ecodes.BTN_SOUTH, evdev.ecodes.BTN_EAST, evdev.ecodes.BTN_NORTH,
                    evdev.ecodes.BTN_WEST, evdev.ecodes.BTN_START, evdev.ecodes.BTN_SELECT}
    return bool(keys & gamepad_keys)


def matches_identity(name: str, vendor_id: str, product_id: str,
                     uniq: str, config: Config) -> bool:
    return (not config.gamepad_name or config.gamepad_name.casefold() in name.casefold()) and (
        not config.gamepad_vendor_id or config.gamepad_vendor_id == vendor_id.lower()) and (
        not config.gamepad_product_id or config.gamepad_product_id == product_id.lower()) and (
        not config.gamepad_uniq or config.gamepad_uniq == uniq)


class Watcher:
    def __init__(self, config: Config):
        self.config = config
        self.device: Any = None
        self.path = ""
        self.pressed: set[int] = set()
        self.next_scan = 0.0
        evdev = _evdev()
        try:
            self.combo = {getattr(evdev.ecodes, name) for name in config.activation_buttons}
        except AttributeError as exc:
            raise ValueError(f"botão de ativação desconhecido: {exc}") from exc

    def close(self) -> None:
        if self.device:
            self.device.close()
            self.device = None
        self.path = ""
        self.pressed.clear()

    def poll(self, timeout: float = 0.25) -> tuple[bool, bool]:
        """Return (device_present, activation_input_pressed_now).

        Without a configured combo, any gamepad button can wake an already-present
        receiver. A newly attached controller still activates on connection.
        """
        evdev = _evdev()
        now = time.monotonic()
        if now >= self.next_scan:
            self.next_scan = now + 1.0
            paths = set(evdev.list_devices())
            if self.path and self.path not in paths:
                LOG.info("Controle desconectado: %s", self.path)
                self.close()
            if not self.device:
                for path in sorted(paths):
                    try:
                        device = evdev.InputDevice(path)
                        if is_gamepad(device, self.config):
                            self.device, self.path = device, path
                            LOG.info("Controle conectado: %s (%s)", device.name, path)
                            break
                        device.close()
                    except (OSError, PermissionError):
                        continue
        if not self.device:
            time.sleep(timeout)
            return False, False
        try:
            readable, _, _ = select.select([self.device.fd], [], [], timeout)
            if not readable:
                return True, False
            activated = False
            for event in self.device.read():
                if event.type != evdev.ecodes.EV_KEY:
                    continue
                if event.value == 1:
                    self.pressed.add(event.code)
                    activated = activated or (self.combo <= self.pressed if self.combo else True)
                elif event.value == 0:
                    self.pressed.discard(event.code)
            return True, activated
        except (OSError, ValueError):
            self.close()
            return False, False
