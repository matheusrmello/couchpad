from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

from . import __version__, audio, displays, discovery, gamepad
from .config import config_path, custom_launcher_command, load, set_enabled, state_path
from .control import ControlServer, request, socket_path
from .notifications import CountdownNotification
from .session import Session, single_instance
from .system import CommandError


LOG = logging.getLogger(__name__)


def doctor(config_file: Path | None) -> None:
    path = config_file or config_path()
    print(f"CouchPad {__version__}")
    print(f"Configuração: {path} ({'presente' if path.exists() else 'ausente'})")
    print(f"Estado pendente: {'sim' if state_path().exists() else 'não'}")
    try:
        config = load(path)
        print(f"Perfil: {config.mode}; desktop={config.desktop_output}; TV={config.tv_output}")
        print(f"Automação: {'ativada' if config.enabled else 'desativada'}")
    except (OSError, ValueError) as exc:
        config = None
        print(f"Configuração indisponível: {exc}")
    try:
        snapshot = displays.capture()
        for item in snapshot["outputs"]:
            print(f"Tela: {item['name']} | conectada={item['connected']} | ativa={item['enabled']}")
            if item["connected"] and (digest := displays.edid_sha256(item["name"])):
                print(f"  EDID SHA-256: {digest}")
        if config:
            if state_path().exists():
                print("Perfil de TV já ativo; a configuração anterior está salva para restauração")
            else:
                print("Plano: " + " ".join(displays.switch_plan(config, snapshot)))
    except (CommandError, ValueError) as exc:
        print(f"Telas: {exc}")
    try:
        default = audio.default_sink()
        print(f"Áudio padrão: {default}")
        for name in sorted(audio.sinks()):
            print(f"Saída de áudio: {name}")
    except CommandError as exc:
        print(f"Áudio: {exc}")
    try:
        controllers = gamepad.candidate_names(config) if config else []
        for name in controllers:
            print(f"Controle: {name}")
        if config and not controllers:
            print("Controle: nenhum acessível nesta sessão")
    except (OSError, RuntimeError) as exc:
        print(f"Controles: {exc}")


def preview(config_file: Path | None) -> None:
    config = load(config_file)
    snapshot = displays.capture()
    print(json.dumps({
        "automation_enabled": config.enabled,
        "display_command": displays.switch_plan(config, snapshot),
        "audio_target": config.tv_sink or "detectar novo HDMI; manter áudio se ambíguo",
        "launcher_start": config.launcher_start,
        "custom_launcher": (custom_launcher_command(config.custom_launcher_path,
                                                    config.custom_launcher_args)
                            if config.custom_launcher_enabled else []),
        "custom_launcher_close": config.custom_launcher_close,
        "cec_on": config.cec_on,
        "changes_applied": False,
    }, indent=2, ensure_ascii=False))


def daemon(config_file: Path | None, session: Session) -> None:
    config = load(config_file)
    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if session.pending():
        LOG.warning("Restaurando sessão deixada por execução anterior")
        session.restore()
    watcher = gamepad.Watcher(config)
    countdown = CountdownNotification()
    connected_before = watcher.poll(0)[0]
    armed = False
    blocked = connected_before or not config.enabled
    wake_on_input = connected_before and config.enabled
    input_started_session = False
    connect_at: float | None = None
    disconnect_at: float | None = None
    active = False
    manual_active = False
    next_display_check = 0.0

    def handle(command: str) -> dict[str, object]:
        nonlocal active, manual_active, armed, blocked, wake_on_input, input_started_session
        nonlocal connect_at, disconnect_at
        nonlocal config, watcher, connected_before
        if command == "status":
            return {"ok": True, "active": active, "enabled": config.enabled, "manual": manual_active,
                    "controller": watcher.device.name if watcher.device else "",
                    "mode": config.mode,
                    "awaiting_input": bool(config.enabled and wake_on_input and connected_before
                                           and not active),
                    "awaiting_reconnect": bool(config.enabled and blocked and connected_before
                                                and not wake_on_input and not active),
                    "countdown_pending": bool(config.enabled and armed and connect_at is not None
                                              and not active and not blocked)}
        if command == "cancel":
            if not (config.enabled and armed and connect_at is not None and not active and not blocked):
                return {"ok": False, "error": "nenhuma troca automática pendente"}
            countdown.cancel()
            armed = False
            connect_at = None
            blocked = True
            wake_on_input = bool(watcher.device and connected_before and config.enabled)
            input_started_session = False
            LOG.info("Troca automática cancelada pela bandeja; aguardando novo acionamento")
            return {"ok": True, "countdown_pending": False}
        if command == "reload":
            updated = load(config_file)
            if active and not updated.enabled:
                session.restore()
                active = False
                manual_active = False
            if ((updated.tv_output, updated.tv_edid_sha256, updated.tv_sink) !=
                    (config.tv_output, config.tv_edid_sha256, config.tv_sink)):
                countdown.cancel()
                armed = False
                connect_at = None
                blocked = connected_before or not updated.enabled
                wake_on_input = connected_before and updated.enabled
                input_started_session = False
            if updated.enabled != config.enabled:
                countdown.cancel()
                armed = False
                connect_at = None
                disconnect_at = None
                blocked = connected_before or not updated.enabled
                wake_on_input = connected_before and updated.enabled
                input_started_session = False
            if ((updated.gamepad_name, updated.gamepad_vendor_id, updated.gamepad_product_id,
                 updated.gamepad_uniq, updated.activation_buttons) !=
                (config.gamepad_name, config.gamepad_vendor_id, config.gamepad_product_id,
                 config.gamepad_uniq, config.activation_buttons)):
                countdown.cancel()
                replacement = gamepad.Watcher(updated)
                watcher.close()
                watcher = replacement
                connected_before = watcher.poll(0)[0]
                blocked = connected_before or not updated.enabled
                wake_on_input = connected_before and updated.enabled
                input_started_session = False
                armed = False
            config = updated
            LOG.info("Configuração recarregada pela interface")
            return {"ok": True, "active": active, "enabled": config.enabled, "mode": config.mode}
        if command in {"enable", "disable"}:
            target_enabled = command == "enable"
            if config.enabled == target_enabled and not (not target_enabled and session.pending()):
                return {"ok": True, "active": active, "enabled": config.enabled}
            if not target_enabled and session.pending():
                session.restore()
                active = False
                manual_active = False
            set_enabled(target_enabled, config_file)
            config = load(config_file)
            countdown.cancel()
            armed = False
            connect_at = None
            disconnect_at = None
            blocked = connected_before or not target_enabled
            wake_on_input = connected_before and target_enabled
            input_started_session = False
            LOG.info("CouchPad %s pela interface", "ativado" if target_enabled else "desativado")
            return {"ok": True, "active": active, "enabled": config.enabled}
        if command == "activate":
            if not config.enabled:
                return {"ok": False, "error": "CouchPad desativado; ative-o para usar a TV"}
            if not active:
                try:
                    session.activate(config)
                except Exception:
                    countdown.cancel()
                    raise
                active = True
                manual_active = watcher.device is None
                disconnect_at = None
                wake_on_input = False
                input_started_session = False
                countdown.activated()
                LOG.info("Perfil de TV ativado pela interface")
            return {"ok": True, "active": True}
        if session.pending():
            session.restore()
        active = False
        manual_active = False
        blocked = watcher.device is not None
        wake_on_input = bool(input_started_session and watcher.device and config.enabled)
        input_started_session = False
        armed = False
        disconnect_at = None
        countdown.cancel()
        LOG.info("Configuração anterior restaurada pela interface")
        return {"ok": True, "active": False}

    try:
        with ControlServer() as control:
            while not stopping:
                connected, activation_pressed = watcher.poll()
                now = time.monotonic()
                if connected and not connected_before:
                    countdown.cancel()
                    armed = config.enabled and not config.activation_buttons
                    blocked = not config.enabled
                    wake_on_input = False
                    input_started_session = False
                    connect_at = now + config.connect_delay
                    disconnect_at = None
                if activation_pressed and config.enabled:
                    if blocked and wake_on_input:
                        blocked = False
                        wake_on_input = False
                        input_started_session = True
                    if not blocked:
                        if not armed:
                            connect_at = now + config.connect_delay
                        armed = True
                if not connected and connected_before:
                    countdown.cancel()
                    armed = False
                    connect_at = None
                    wake_on_input = False
                    input_started_session = False
                    if active and not manual_active:
                        disconnect_at = now + config.disconnect_delay
                if connected:
                    disconnect_at = None
                if (config.enabled and connected and armed and not active and not blocked
                        and connect_at is not None and now < connect_at):
                    countdown.show(connect_at - now, config.tv_output)
                if config.enabled and connected and armed and not active and not blocked and connect_at is not None and now >= connect_at:
                    try:
                        session.activate(config)
                        active = True
                        manual_active = False
                        countdown.activated()
                        LOG.info("Perfil de TV ativado")
                    except Exception:
                        countdown.cancel()
                        blocked = True
                        wake_on_input = False
                        input_started_session = False
                        LOG.exception("Falha ao ativar; aguardando reconexão do controle")
                if not connected and active and disconnect_at is not None and now >= disconnect_at:
                    session.restore()
                    active = False
                    disconnect_at = None
                    input_started_session = False
                    LOG.info("Configuração anterior restaurada")
                if active and now >= next_display_check:
                    next_display_check = now + 3.0
                    try:
                        tv = displays.output(displays.capture(), config.tv_output)
                        if not tv.get("connected"):
                            LOG.warning("TV desconectada; restaurando monitor principal")
                            session.restore()
                            active = False
                            manual_active = False
                            blocked = True
                            wake_on_input = False
                            input_started_session = False
                    except (CommandError, ValueError) as exc:
                        LOG.warning("Não foi possível verificar a TV: %s", exc)
                connected_before = connected
                control.poll(handle)
    finally:
        countdown.cancel()
        watcher.close()
        if session.pending():
            session.restore()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Troca de TV e áudio para KDE Plasma/Wayland")
    parser.add_argument("--config", type=Path, help="arquivo TOML de configuração")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "devices", "preview", "switch", "restore", "status", "enable", "disable", "cancel", "run", "tray", "qt"):
        sub.add_parser(name)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    session = Session()
    try:
        if args.command == "doctor":
            doctor(args.config)
        elif args.command == "devices":
            print(json.dumps(discovery.scan(load(args.config)), ensure_ascii=False, indent=2))
        elif args.command == "preview":
            preview(args.config)
        elif args.command == "tray":
            from .tray import main as tray_main
            tray_main()
        elif args.command == "qt":
            from .qt_frontend import main as qt_main
            return qt_main()
        elif args.command == "status":
            print(json.dumps(request("status"), ensure_ascii=False, indent=2))
        elif args.command == "cancel":
            response = request("cancel")
            if not response.get("ok"):
                raise RuntimeError(str(response.get("error", "falha ao cancelar a troca")))
            print("Troca automática cancelada; reconecte o controle para tentar novamente")
        elif args.command in {"enable", "disable"}:
            if socket_path().exists():
                response = request(args.command)
                if not response.get("ok"):
                    raise RuntimeError(str(response.get("error", "falha ao alterar estado")))
            else:
                with single_instance(session.path):
                    if args.command == "disable" and session.pending():
                        session.restore()
                    set_enabled(args.command == "enable", args.config)
            print("CouchPad ativado" if args.command == "enable" else "CouchPad desativado")
        else:
            if args.command in {"switch", "restore"} and socket_path().exists():
                response = request("activate" if args.command == "switch" else "restore")
                if not response.get("ok"):
                    raise RuntimeError(str(response.get("error", "falha no serviço")))
                print("Perfil de TV ativado" if args.command == "switch" else "Configuração restaurada")
                return 0
            with single_instance(session.path):
                if args.command == "switch":
                    config = load(args.config)
                    if not config.enabled:
                        raise RuntimeError("CouchPad desativado; ative-o para usar a TV")
                    session.activate(config)
                    print("Perfil de TV ativado; use 'restore' para voltar")
                elif args.command == "restore":
                    print("Configuração restaurada" if session.restore() else "Nenhuma sessão pendente")
                elif args.command == "run":
                    daemon(args.config, session)
        return 0
    except (OSError, ValueError, RuntimeError, CommandError) as exc:
        LOG.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
