from __future__ import annotations

import json
import time

from .system import CommandError, run


def default_sink() -> str:
    return run(["pactl", "get-default-sink"]).strip()


def sinks() -> set[str]:
    rows = run(["pactl", "list", "short", "sinks"])
    return {parts[1] for line in rows.splitlines() if len(parts := line.split()) >= 2}


def capture_volumes() -> dict[str, list[int]]:
    try:
        items = json.loads(run(["pactl", "-f", "json", "list", "sinks"]))
    except json.JSONDecodeError as exc:
        raise CommandError("pactl retornou volumes inválidos") from exc
    if not isinstance(items, list):
        raise CommandError("pactl não retornou a lista de saídas")
    result = {}
    for item in items:
        channels = item.get("volume", {}).values()
        values = [channel.get("value") for channel in channels]
        if values and all(isinstance(value, int) and value >= 0 for value in values):
            result[item["name"]] = values
    return result


def set_volume(name: str, values: list[int] | str) -> None:
    levels = [values] if isinstance(values, str) else [str(value) for value in values]
    run(["pactl", "set-sink-volume", name, *levels])


def restore_volumes(saved: dict[str, list[int]]) -> None:
    available = sinks()
    for name, values in saved.items():
        if name in available:
            set_volume(name, values)


def cards() -> list[dict]:
    try:
        result = json.loads(run(["pactl", "-f", "json", "list", "cards"]))
    except json.JSONDecodeError as exc:
        raise CommandError("pactl retornou perfis de áudio inválidos") from exc
    if not isinstance(result, list):
        raise CommandError("pactl não retornou a lista de placas")
    return result


def capture_profiles() -> dict[str, str]:
    return {card["name"]: card["active_profile"] for card in cards()
            if isinstance(card.get("name"), str) and isinstance(card.get("active_profile"), str)}


def restore_profiles(saved: dict[str, str]) -> None:
    for card in cards():
        profile = saved.get(card.get("name"))
        if profile and profile != card.get("active_profile") and profile in card.get("profiles", {}):
            run(["pactl", "set-card-profile", card["name"], profile])


def activate_tv_profile(model: str) -> bool:
    """Expose a TV sink when a shared HDMI card still uses the PC profile."""
    if not model.strip():
        return False
    matches = []
    for card in cards():
        for port in card.get("ports", {}).values():
            if (str(port.get("type", "")).casefold() == "hdmi"
                    and port.get("availability") == "available"
                    and str(port.get("properties", {}).get("device.product.name", "")).strip().casefold()
                    == model.strip().casefold()):
                profiles = [(name, card.get("profiles", {}).get(name, {}))
                            for name in port.get("profiles", []) if name.startswith("output:hdmi-stereo")]
                if profiles:
                    selected = max(profiles, key=lambda item: item[1].get("priority", 0))[0]
                    matches.append((card, selected))
    if len(matches) != 1:
        return False
    card, profile = matches[0]
    if card.get("active_profile") == profile:
        return False
    run(["pactl", "set-card-profile", card["name"], profile])
    return True


def sink_details() -> list[dict[str, str]]:
    """Current PipeWire/PulseAudio sinks with HDMI monitor identity when exposed."""
    try:
        raw = json.loads(run(["pactl", "-f", "json", "list", "sinks"]))
    except json.JSONDecodeError as exc:
        raise CommandError("pactl retornou JSON inválido") from exc
    if not isinstance(raw, list):
        raise CommandError("pactl não retornou a lista de saídas")
    result = []
    for item in raw:
        props = item.get("properties", {})
        result.append({
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "monitor_name": props.get("alsa.name") or props.get("node.nick") or "",
            "port": item.get("active_port", ""),
        })
    return result


def matching_model(sink_list: list[dict[str, str]], model: str) -> list[dict[str, str]]:
    model = model.casefold().strip()
    if not model:
        return []
    return [sink for sink in sink_list if "hdmi" in sink["name"].casefold() and
            (model == sink["monitor_name"].casefold().strip() or
             f"[{model}]" in sink["description"].casefold())]


def choose_sink(configured: str, previous: set[str], original: str,
                wait: float = 10, tv_model: str = "") -> str | None:
    deadline = time.monotonic() + wait
    profile_activated = False
    while True:
        available = sinks()
        if configured and configured in available:
            return configured
        if tv_model:
            matches = matching_model(sink_details(), tv_model)
            if len(matches) == 1:
                return matches[0]["name"]
            if len(matches) > 1:
                return None
        candidates = [x for x in available - previous if "hdmi" in x.lower() and x != original]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            return None
        if tv_model and not profile_activated:
            profile_activated = activate_tv_profile(tv_model)
            if profile_activated:
                continue
        if time.monotonic() >= deadline:
            if configured:
                raise CommandError(f"saída de áudio {configured!r} não apareceu")
            return None
        time.sleep(0.5)


def set_default(name: str) -> None:
    if name and name in sinks():
        run(["pactl", "set-default-sink", name])
