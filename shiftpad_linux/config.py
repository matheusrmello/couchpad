from __future__ import annotations

import os
import re
import json
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


STEAM_START = ("/usr/bin/steam", "steam://open/bigpicture")
STEAM_STOP = ("/usr/bin/steam", "steam://close/bigpicture")


def custom_launcher_command(path: str, args: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Launch a chosen executable or a Linux desktop entry without a shell."""
    if Path(path).suffix.casefold() == ".desktop":
        if args:
            raise ValueError("atalhos .desktop não aceitam argumentos adicionais")
        return ("gio", "launch", path)
    return (path, *args)


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "shiftpad-linux" / "config.toml"


def state_path() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "shiftpad-linux" / "session.json"


@dataclass(frozen=True)
class Config:
    desktop_output: str
    tv_output: str
    enabled: bool = True
    tv_edid_sha256: str = ""
    mode: str = "tv-only"
    tv_sink: str = ""
    gamepad_name: str = ""
    gamepad_vendor_id: str = ""
    gamepad_product_id: str = ""
    gamepad_uniq: str = ""
    activation_buttons: tuple[str, ...] = ()
    connect_delay: float = 2.0
    disconnect_delay: float = 2.0
    launcher_start: tuple[str, ...] = ()
    launcher_stop: tuple[str, ...] = ()
    custom_launcher_path: str = ""
    custom_launcher_enabled: bool = False
    custom_launcher_close: bool = False
    custom_launcher_args: tuple[str, ...] = ()
    cec_on: tuple[str, ...] = ()
    cec_off: tuple[str, ...] = ()


def _command(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
        raise ValueError(f"{name} deve ser uma lista de strings não vazias")
    return tuple(value)


def load(path: Path | None = None) -> Config:
    path = path or config_path()
    with path.open("rb") as file:
        raw = tomllib.load(file)
    general = raw.get("general", {})
    display = raw.get("display", {})
    audio = raw.get("audio", {})
    gamepad = raw.get("gamepad", {})
    launcher = raw.get("launcher", {})
    cec = raw.get("cec", {})
    if not all(isinstance(x, dict) for x in (general, display, audio, gamepad, launcher, cec)):
        raise ValueError("seções de configuração inválidas")
    enabled = general.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("general.enabled deve ser true ou false")
    desktop = display.get("desktop_output", "")
    tv = display.get("tv_output", "")
    if not isinstance(desktop, str) or not isinstance(tv, str) or not desktop or not tv or desktop == tv:
        raise ValueError("defina desktop_output e tv_output distintos")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", desktop) or not re.fullmatch(r"[A-Za-z0-9_-]+", tv):
        raise ValueError("nomes de saída de vídeo inválidos")
    tv_edid_sha256 = display.get("tv_edid_sha256", "")
    if not isinstance(tv_edid_sha256, str) or (tv_edid_sha256 and not re.fullmatch(r"[0-9a-fA-F]{64}", tv_edid_sha256)):
        raise ValueError("display.tv_edid_sha256 deve ser um SHA-256 hexadecimal")
    mode = display.get("mode", "tv-only")
    if mode not in ("tv-only", "extend", "mirror"):
        raise ValueError("display.mode deve ser tv-only, extend ou mirror")
    buttons = gamepad.get("activation_buttons", [])
    if not isinstance(buttons, list) or not all(isinstance(x, str) and x.startswith("BTN_") for x in buttons):
        raise ValueError("gamepad.activation_buttons deve conter nomes BTN_*")
    try:
        connect_delay = float(gamepad.get("connect_delay", 2))
        disconnect_delay = float(gamepad.get("disconnect_delay", 2))
    except (TypeError, ValueError) as exc:
        raise ValueError("atrasos do gamepad devem ser números") from exc
    if not 0 <= connect_delay <= 300 or not 0 <= disconnect_delay <= 300:
        raise ValueError("atrasos do gamepad devem estar entre 0 e 300 segundos")
    sink = audio.get("tv_sink", "")
    name = gamepad.get("name_contains", "")
    if not isinstance(sink, str) or not isinstance(name, str):
        raise ValueError("audio.tv_sink e gamepad.name_contains devem ser strings")
    vendor_id = gamepad.get("vendor_id", "")
    product_id = gamepad.get("product_id", "")
    uniq = gamepad.get("uniq", "")
    if (not isinstance(vendor_id, str) or not isinstance(product_id, str)
            or not isinstance(uniq, str)
            or any(value and not re.fullmatch(r"[0-9a-fA-F]{4}", value)
                   for value in (vendor_id, product_id))
            or bool(vendor_id) != bool(product_id)
            or any(ord(char) < 32 for char in uniq)):
        raise ValueError("identidade do controle inválida")
    custom_path = launcher.get("custom_path", "")
    custom_enabled = launcher.get("custom_enabled", False)
    custom_close = launcher.get("custom_close", False)
    custom_args = _command(launcher.get("custom_args", []), "launcher.custom_args")
    if not isinstance(custom_path, str) or not isinstance(custom_enabled, bool) or not isinstance(custom_close, bool):
        raise ValueError("launcher.custom_path, custom_enabled ou custom_close inválidos")
    if custom_enabled and (not custom_path or not Path(custom_path).is_absolute()):
        raise ValueError("launcher.custom_path deve ser um caminho absoluto quando ativado")
    if custom_enabled and custom_close and Path(custom_path).suffix.casefold() == ".desktop":
        raise ValueError("encerramento automático exige executável ou AppImage, não atalho .desktop")
    if custom_enabled:
        custom_launcher_command(custom_path, custom_args)
    return Config(
        desktop_output=desktop,
        tv_output=tv,
        enabled=enabled,
        tv_edid_sha256=tv_edid_sha256.lower(),
        mode=mode,
        tv_sink=sink,
        gamepad_name=name,
        gamepad_vendor_id=vendor_id.lower(),
        gamepad_product_id=product_id.lower(),
        gamepad_uniq=uniq,
        activation_buttons=tuple(buttons),
        connect_delay=connect_delay,
        disconnect_delay=disconnect_delay,
        launcher_start=_command(launcher.get("start", []), "launcher.start"),
        launcher_stop=_command(launcher.get("stop", []), "launcher.stop"),
        custom_launcher_path=custom_path,
        custom_launcher_enabled=custom_enabled,
        custom_launcher_close=custom_close,
        custom_launcher_args=custom_args,
        cec_on=_command(cec.get("on", []), "cec.on"),
        cec_off=_command(cec.get("off", []), "cec.off"),
    )


def save_basic_settings(mode: str, connect_delay: float, disconnect_delay: float,
                        steam_enabled: bool | None, path: Path | None = None, *,
                        custom_launcher_path: str | None = None,
                        custom_launcher_enabled: bool | None = None,
                        custom_launcher_close: bool | None = None,
                        custom_launcher_args: tuple[str, ...] | None = None,
                        tv_output: str | None = None,
                        tv_edid_sha256: str | None = None,
                        tv_sink: str | None = None,
                        gamepad_name: str | None = None,
                        gamepad_vendor_id: str | None = None,
                        gamepad_product_id: str | None = None,
                        gamepad_uniq: str | None = None) -> None:
    """Update settings exposed in the UI while preserving other TOML entries."""
    path = path or config_path()
    current = load(path)
    if mode not in {"tv-only", "extend", "mirror"}:
        raise ValueError("modo de vídeo inválido")
    if not 0 <= connect_delay <= 300 or not 0 <= disconnect_delay <= 300:
        raise ValueError("atrasos devem estar entre 0 e 300 segundos")
    updates = {
        ("display", "mode"): json.dumps(mode),
        ("gamepad", "connect_delay"): str(connect_delay),
        ("gamepad", "disconnect_delay"): str(disconnect_delay),
    }
    target_tv = tv_output if tv_output is not None else current.tv_output
    target_edid = tv_edid_sha256 if tv_edid_sha256 is not None else current.tv_edid_sha256
    target_sink = tv_sink if tv_sink is not None else current.tv_sink
    target_name = gamepad_name if gamepad_name is not None else current.gamepad_name
    target_vendor = gamepad_vendor_id if gamepad_vendor_id is not None else current.gamepad_vendor_id
    target_product = gamepad_product_id if gamepad_product_id is not None else current.gamepad_product_id
    target_uniq = gamepad_uniq if gamepad_uniq is not None else current.gamepad_uniq
    if (not isinstance(target_tv, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", target_tv)
            or target_tv == current.desktop_output
            or not isinstance(target_edid, str)
            or (target_edid and not re.fullmatch(r"[0-9a-fA-F]{64}", target_edid))):
        raise ValueError("TV ou identidade da tela inválida")
    if not isinstance(target_sink, str) or (target_sink and not re.fullmatch(r"[A-Za-z0-9._-]+", target_sink)):
        raise ValueError("nome da saída de áudio inválido")
    if (not isinstance(target_name, str) or any(ord(char) < 32 for char in target_name)
            or not isinstance(target_vendor, str) or not isinstance(target_product, str)
            or any(value and not re.fullmatch(r"[0-9a-fA-F]{4}", value)
                   for value in (target_vendor, target_product))
            or bool(target_vendor) != bool(target_product)
            or not isinstance(target_uniq, str)
            or any(ord(char) < 32 for char in target_uniq)):
        raise ValueError("controle selecionado inválido")
    if tv_output is not None or tv_edid_sha256 is not None:
        updates[("display", "tv_output")] = json.dumps(target_tv)
        updates[("display", "tv_edid_sha256")] = json.dumps(target_edid.lower())
    if tv_sink is not None:
        updates[("audio", "tv_sink")] = json.dumps(target_sink)
    if any(value is not None for value in (gamepad_name, gamepad_vendor_id,
                                           gamepad_product_id, gamepad_uniq)):
        updates[("gamepad", "name_contains")] = json.dumps(target_name, ensure_ascii=False)
        updates[("gamepad", "vendor_id")] = json.dumps(target_vendor.lower())
        updates[("gamepad", "product_id")] = json.dumps(target_product.lower())
        updates[("gamepad", "uniq")] = json.dumps(target_uniq, ensure_ascii=False)
    if steam_enabled is not None:
        if current.launcher_start not in ((), STEAM_START):
            raise ValueError("launcher personalizado: edite o arquivo TOML para preservá-lo")
        updates[("launcher", "start")] = json.dumps(STEAM_START if steam_enabled else ())
        updates[("launcher", "stop")] = json.dumps(STEAM_STOP if steam_enabled else ())
    if (custom_launcher_path is not None or custom_launcher_enabled is not None
            or custom_launcher_close is not None
            or custom_launcher_args is not None):
        selected = custom_launcher_path if custom_launcher_path is not None else current.custom_launcher_path
        enabled = custom_launcher_enabled if custom_launcher_enabled is not None else current.custom_launcher_enabled
        close = custom_launcher_close if custom_launcher_close is not None else current.custom_launcher_close
        args = custom_launcher_args if custom_launcher_args is not None else current.custom_launcher_args
        if (not isinstance(selected, str) or not isinstance(enabled, bool) or not isinstance(close, bool)
                or not isinstance(args, tuple) or not all(isinstance(arg, str) and arg for arg in args)):
            raise ValueError("inicializador personalizado inválido")
        selected_path = Path(selected)
        if enabled and (not selected_path.is_absolute() or not selected_path.is_file()
                        or (selected_path.suffix.casefold() != ".desktop" and
                            not os.access(selected, os.X_OK))):
            raise ValueError("selecione um executável, AppImage ou atalho .desktop")
        if enabled:
            custom_launcher_command(selected, args)
        if enabled and close and selected_path.suffix.casefold() == ".desktop":
            raise ValueError("encerramento automático exige executável ou AppImage, não atalho .desktop")
        updates[("launcher", "custom_path")] = json.dumps(selected, ensure_ascii=False)
        updates[("launcher", "custom_enabled")] = "true" if enabled else "false"
        updates[("launcher", "custom_close")] = "true" if close else "false"
        updates[("launcher", "custom_args")] = json.dumps(args, ensure_ascii=False)
    _write_updates(path, updates)


def set_enabled(enabled: bool, path: Path | None = None) -> None:
    """Persist the automation toggle independently from other unsaved settings."""
    if not isinstance(enabled, bool):
        raise ValueError("enabled deve ser booleano")
    path = path or config_path()
    load(path)
    _write_updates(path, {("general", "enabled"): "true" if enabled else "false"})


def _write_updates(path: Path, updates: dict[tuple[str, str], str]) -> None:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    output: list[str] = []
    seen: set[tuple[str, str]] = set()
    section = ""
    found_sections: set[str] = set()

    def append_missing(current_section: str) -> None:
        for (target_section, key), value in updates.items():
            if target_section == current_section and (target_section, key) not in seen:
                output.append(f"{key} = {value}")
                seen.add((target_section, key))

    for line in lines:
        header = re.fullmatch(r"\s*\[([A-Za-z0-9_-]+)\]\s*", line)
        if header:
            append_missing(section)
            section = header.group(1)
            found_sections.add(section)
            output.append(line)
            continue
        key_match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=", line)
        if key_match and (section, key_match.group(1)) in updates:
            key = key_match.group(1)
            output.append(f"{key} = {updates[(section, key)]}")
            seen.add((section, key))
        else:
            output.append(line)
    append_missing(section)
    for target_section in ("general", "display", "audio", "gamepad", "launcher"):
        if target_section not in found_sections and any(key[0] == target_section for key in updates):
            output.extend(["", f"[{target_section}]"])
            append_missing(target_section)
    content = "\n".join(output).rstrip() + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".config-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
