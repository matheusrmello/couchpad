"""Read-only identification of displays, audio endpoints and gamepads."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import audio, displays, gamepad
from .config import Config, state_path
from .system import CommandError


PNP_IDS = Path("/usr/share/hwdata/pnp.ids")


def parse_edid(data: bytes, vendors: dict[str, str] | None = None) -> dict[str, str | int]:
    """Decode identity fields from a display's base EDID block."""
    if len(data) < 128 or data[:8] != b"\x00\xff\xff\xff\xff\xff\xff\x00":
        raise ValueError("EDID inválido")
    word = int.from_bytes(data[8:10], "big")
    code = "".join(chr(64 + ((word >> shift) & 31)) for shift in (10, 5, 0))
    model = ""
    for offset in (54, 72, 90, 108):
        block = data[offset:offset + 18]
        if block[:5] == b"\x00\x00\x00\xfc\x00":
            model = block[5:18].split(b"\n", 1)[0].decode("ascii", "replace").strip()
            break
    return {
        "manufacturer_code": code,
        "manufacturer": (vendors or {}).get(code, code),
        "model": model,
        "product_code": int.from_bytes(data[10:12], "little"),
        "edid_sha256": hashlib.sha256(data).hexdigest(),
    }


def vendor_names(path: Path = PNP_IDS) -> dict[str, str]:
    names: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if len(line) > 4 and line[3] == "\t":
                names[line[:3]] = line[4:].strip()
    except OSError:
        pass
    return names


def read_edid(output: str) -> bytes | None:
    found: set[bytes] = set()
    for path in Path("/sys/class/drm").glob(f"*-{output}/edid"):
        try:
            raw = path.read_bytes()
            if raw:
                found.add(raw)
        except OSError:
            continue
    return next(iter(found)) if len(found) == 1 else None


def display_devices() -> list[dict[str, Any]]:
    vendors = vendor_names()
    result = []
    for item in displays.capture()["outputs"]:
        mode = next((m for m in item.get("modes", []) if m.get("id") == item.get("currentModeId")), {})
        size = mode.get("size", {})
        entry: dict[str, Any] = {
            "output": item["name"],
            "connected": bool(item.get("connected")),
            "enabled": bool(item.get("enabled")),
            "resolution": (f"{size['width']} × {size['height']}" if size.get('width') and size.get('height') else ""),
        }
        raw = read_edid(item["name"]) if entry["connected"] else None
        if raw:
            try:
                entry.update(parse_edid(raw, vendors))
            except ValueError:
                pass
        entry["label"] = (entry.get("model") or entry.get("manufacturer") or "Tela") + f" ({item['name']})"
        result.append(entry)
    return result


def audio_devices() -> list[dict[str, str]]:
    return audio.sink_details()


def matching_tv_audio(sinks: list[dict[str, str]], display: dict[str, Any]) -> list[dict[str, str]]:
    """Match a live HDMI sink to the EDID monitor name, without guessing on ambiguity."""
    return audio.matching_model(sinks, str(display.get("model", "")))


def gamepad_devices() -> list[dict[str, str]]:
    evdev = gamepad._evdev()
    any_controller = Config(desktop_output="_desktop", tv_output="_tv")
    found = []
    for path in evdev.list_devices():
        try:
            device = evdev.InputDevice(path)
            try:
                if gamepad.is_gamepad(device, any_controller):
                    found.append({
                        "path": path,
                        "model": device.name,
                        "vendor_id": f"{device.info.vendor:04x}",
                        "product_id": f"{device.info.product:04x}",
                        "bus": f"{device.info.bustype:04x}",
                        "uniq": device.uniq or "",
                    })
            finally:
                device.close()
        except (OSError, PermissionError):
            continue
    return found


def scan(config: Config) -> dict[str, Any]:
    """Return evidence and confidence for configured hardware, without changing it."""
    result: dict[str, Any] = {"displays": [], "audio": [], "gamepads": [], "errors": {}}
    for key, discover in (("displays", display_devices), ("audio", audio_devices),
                          ("gamepads", gamepad_devices)):
        try:
            result[key] = discover()
        except (CommandError, OSError, ValueError, RuntimeError) as exc:
            result["errors"][key] = str(exc)
    target = next((x for x in result["displays"] if x["output"] == config.tv_output), None)
    if target and config.tv_edid_sha256:
        target["configured_match"] = target.get("edid_sha256") == config.tv_edid_sha256
    elif target:
        target["configured_match"] = None
    result["tv"] = target
    matches = matching_tv_audio(result["audio"], target) if target else []
    result["tv_audio"] = matches[0] if len(matches) == 1 else None
    result["tv_audio_method"] = "monitor-name" if result["tv_audio"] else ""
    result["audio_ambiguous"] = len(matches) > 1
    result["configured_audio"] = next((x for x in result["audio"] if x["name"] == config.tv_sink), None)
    if target and target.get("enabled") and target.get("configured_match") is not False and not result["tv_audio"]:
        try:
            session = json.loads(state_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            session = {}
        if session.get("tv_output") == config.tv_output:
            selected = session.get("tv_audio_sink", "")
            result["tv_audio"] = next((x for x in result["audio"] if x["name"] == selected), None)
            if result["tv_audio"]:
                result["tv_audio_method"] = "active-session"
        if not result["tv_audio"] and result["configured_audio"]:
            result["tv_audio"] = result["configured_audio"]
            result["tv_audio_method"] = "configured"
    result["configured_gamepads"] = [x for x in result["gamepads"] if
                                     gamepad.matches_identity(x["model"], x["vendor_id"],
                                                              x["product_id"], x.get("uniq", ""), config)]
    return result
