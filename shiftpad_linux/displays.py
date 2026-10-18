from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from .config import Config
from .system import CommandError, run


def capture() -> dict[str, Any]:
    try:
        data = json.loads(run(["kscreen-doctor", "-j"]))
    except (json.JSONDecodeError, KeyError) as exc:
        raise CommandError("resposta JSON inválida de kscreen-doctor") from exc
    if not isinstance(data.get("outputs"), list):
        raise CommandError("kscreen-doctor não informou as saídas")
    return data


def output(snapshot: dict[str, Any], name: str) -> dict[str, Any]:
    match = next((x for x in snapshot["outputs"] if x.get("name") == name), None)
    if match is None:
        raise ValueError(f"saída de vídeo {name!r} não encontrada")
    return match


def edid_sha256(name: str) -> str | None:
    hashes = set()
    for path in Path("/sys/class/drm").glob(f"*-{name}/edid"):
        try:
            content = path.read_bytes()
        except OSError:
            continue
        if content:
            hashes.add(hashlib.sha256(content).hexdigest())
    return next(iter(hashes)) if len(hashes) == 1 else None


def is_4k(item: dict[str, Any]) -> bool:
    modes = item.get("modes", [])
    current = next((mode for mode in modes if mode.get("id") == item.get("currentModeId")), {})
    size = current.get("size") or item.get("size") or {}
    dimensions = sorted((size.get("width", 0), size.get("height", 0)))
    return dimensions in ([2160, 3840], [2160, 4096])


def switch_plan(config: Config, snapshot: dict[str, Any]) -> list[str]:
    desktop = output(snapshot, config.desktop_output)
    tv = output(snapshot, config.tv_output)
    if not desktop.get("connected") or not tv.get("connected"):
        raise ValueError("monitor principal e TV precisam estar conectados")
    if config.tv_edid_sha256 and edid_sha256(config.tv_output) != config.tv_edid_sha256:
        raise ValueError("o EDID da saída de TV não corresponde ao aparelho configurado")
    if not desktop.get("enabled"):
        raise ValueError("o monitor principal precisa estar ativo antes da troca")
    args = ["kscreen-doctor", f"output.{config.tv_output}.enable"]
    if is_4k(tv):
        args.append(f"output.{config.tv_output}.scale.2.75")
    if config.mode == "tv-only":
        args.append(f"output.{config.tv_output}.mirror.none")
        args.extend(f"output.{x['name']}.disable" for x in snapshot["outputs"] if x.get("enabled") and x["name"] != config.tv_output)
    elif config.mode == "extend":
        x = desktop["pos"]["x"] + desktop["size"]["width"]
        y = desktop["pos"]["y"]
        args.extend([f"output.{config.tv_output}.mirror.none", f"output.{config.tv_output}.position.{x},{y}"])
    else:
        args.append(f"output.{config.tv_output}.mirror.{config.desktop_output}")
    return args


def restore_plan(saved: dict[str, Any], current: dict[str, Any], desktop_name: str) -> list[str]:
    args = ["kscreen-doctor"]
    now = {x["name"]: x for x in current["outputs"]}
    prior = {x["name"]: x for x in saved["outputs"]}
    if desktop_name not in prior or desktop_name not in now:
        raise ValueError("monitor principal indisponível para restauração")
    # Enable the desktop first. Other saved outputs follow; disconnected ones are skipped.
    names = [desktop_name] + [x for x in prior if x != desktop_name]
    enabled = []
    for name in names:
        previous = prior[name]
        if name not in now or not now[name].get("connected"):
            continue
        scale = previous.get("scale")
        if isinstance(scale, (float, int)) and scale > 0:
            args.append(f"output.{name}.scale.{scale}")
        if previous.get("enabled"):
            enabled.append(name)
            args.append(f"output.{name}.enable")
            mode = previous.get("currentModeId")
            if mode and any(x.get("id") == mode for x in now[name].get("modes", [])):
                args.append(f"output.{name}.mode.{mode}")
            pos = previous.get("pos")
            if isinstance(pos, dict) and "x" in pos and "y" in pos:
                args.append(f"output.{name}.position.{pos['x']},{pos['y']}")
        else:
            args.append(f"output.{name}.disable")
    if not enabled:
        # An unplugged formerly-enabled screen must not leave the user in darkness.
        args = ["kscreen-doctor", f"output.{desktop_name}.enable"]
    else:
        for name in enabled:
            source_id = prior[name].get("replicationSource", 0)
            source = next((x["name"] for x in saved["outputs"] if x.get("id") == source_id), None)
            if source and source in enabled:
                args.append(f"output.{name}.mirror.{source}")
            else:
                args.append(f"output.{name}.mirror.none")
    return args


def hdr_restore_plan(saved: dict[str, Any], current: dict[str, Any],
                     names: set[str] | None = None) -> list[str]:
    """Reapply known HDR/WCG settings after a topology change.

    KScreen omits these fields for incapable outputs. Never enable HDR when
    the saved snapshot did not explicitly report the previous setting.
    """
    prior = {item["name"]: item for item in saved["outputs"]}
    args = ["kscreen-doctor"]
    for item in current["outputs"]:
        name = item["name"]
        if (name not in prior or (names is not None and name not in names)
                or not item.get("connected") or not item.get("enabled")):
            continue
        previous = prior[name]
        for field, setting in (("hdrEnabled", "hdr"), ("wcgEnabled", "wcg")):
            wanted = previous.get(field)
            if isinstance(wanted, bool) and item.get(field) != wanted:
                args.append(f"output.{name}.{setting}.{'enable' if wanted else 'disable'}")
        brightness = previous.get("sdrBrightness")
        if (previous.get("hdrEnabled") is True and isinstance(brightness, int)
                and not isinstance(brightness, bool) and 100 <= brightness <= 1000
                and item.get("sdrBrightness") != brightness):
            args.append(f"output.{name}.sdr-brightness.{brightness}")
    return args


def apply(args: list[str]) -> None:
    run(args, timeout=25)
