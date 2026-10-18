from __future__ import annotations

import fcntl
import json
import logging
import os
import signal
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from . import audio, discovery, displays
from .config import Config, custom_launcher_command, state_path
from .system import CommandError, host_environment, run


LOG = logging.getLogger(__name__)


def _process_identity(pid: int) -> dict[str, str | int] | None:
    """Identify one Linux process across daemon restarts without trusting a reused PID."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        stat = Path(f"/proc/{pid}/stat").read_text()
        start_time = stat.rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        return None
    return {"pid": pid, "boot_id": boot_id, "start_time": start_time}


def _stop_owned_launcher(record: object) -> None:
    """Ask only the exact launcher process started by this session to exit."""
    if not isinstance(record, dict):
        return
    pid = record.get("pid")
    if not isinstance(pid, int) or _process_identity(pid) != record:
        LOG.info("Inicializador personalizado já saiu ou mudou de identidade; nada a encerrar")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        LOG.info("Encerramento solicitado ao inicializador personalizado (PID %s)", pid)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        LOG.warning("Não foi possível encerrar o inicializador personalizado: %s", exc)


@contextmanager
def single_instance(path: Path) -> Iterator[None]:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("outra instância está controlando a sessão") from exc
        yield
    finally:
        os.close(fd)


class Session:
    def __init__(self, path: Path | None = None):
        self.path = path or state_path()

    def pending(self) -> bool:
        return self.path.exists()

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        raw = json.dumps(data, ensure_ascii=False).encode()
        fd, tmp = tempfile.mkstemp(prefix=".session-", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as file:
                file.write(raw)
                file.flush()
                os.fsync(file.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _load(self) -> dict[str, Any]:
        with self.path.open(encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _restore_hdr(saved: dict[str, Any], current: dict[str, Any],
                     names: set[str] | None = None) -> None:
        try:
            plan = displays.hdr_restore_plan(saved, current, names)
            if len(plan) > 1:
                displays.apply(plan)
        except (CommandError, ValueError) as exc:
            LOG.warning("Não foi possível restaurar o estado HDR: %s", exc)

    def activate(self, config: Config) -> None:
        if self.pending():
            raise RuntimeError("há uma sessão pendente; execute restore antes de ativar")
        before_display = displays.capture()
        plan = displays.switch_plan(config, before_display)
        try:
            before_audio = audio.default_sink()
            before_sinks = audio.sinks()
        except CommandError as exc:
            LOG.warning("Áudio indisponível; troca de áudio será ignorada: %s", exc)
            before_audio, before_sinks = "", set()
        try:
            before_profiles = audio.capture_profiles()
        except CommandError as exc:
            LOG.warning("Perfis de áudio indisponíveis: %s", exc)
            before_profiles = {}
        try:
            before_volumes = audio.capture_volumes()
        except CommandError as exc:
            LOG.warning("Volumes de áudio indisponíveis: %s", exc)
            before_volumes = {}
        data = {
            "display": before_display,
            "desktop_output": config.desktop_output,
            "tv_output": config.tv_output,
            "mode": config.mode,
            "audio_sink": before_audio,
            "audio_profiles": before_profiles,
            "audio_volumes": before_volumes,
            "tv_audio_sink": "",
            "launcher_stop": list(config.launcher_stop),
            "cec_off": list(config.cec_off),
            "launcher_started": False,
            "custom_launcher_process": None,
            "cec_enabled": False,
        }
        self._save(data)
        try:
            displays.apply(plan)
            after = displays.capture()
            if not displays.output(after, config.tv_output).get("enabled"):
                raise RuntimeError("TV não ficou ativa após a troca")
            if config.mode == "tv-only" and displays.output(after, config.desktop_output).get("enabled"):
                raise RuntimeError("monitor principal permaneceu ativo no modo tv-only")
            self._restore_hdr(before_display, after, {config.tv_output})
            raw_edid = discovery.read_edid(config.tv_output)
            try:
                tv_model = str(discovery.parse_edid(raw_edid).get("model", "")) if raw_edid else ""
            except ValueError:
                tv_model = ""
            try:
                chosen = audio.choose_sink(config.tv_sink, before_sinks, before_audio,
                                           tv_model=tv_model)
                if chosen:
                    audio.set_default(chosen)
                    data["tv_audio_sink"] = chosen
                    if chosen not in data["audio_volumes"]:
                        volumes = audio.capture_volumes()
                        if chosen not in volumes:
                            raise CommandError("não foi possível salvar o volume anterior da TV")
                        data["audio_volumes"][chosen] = volumes[chosen]
                    self._save(data)
                    audio.set_volume(chosen, "100%")
                else:
                    LOG.info("Nenhuma saída HDMI da TV foi identificada sem ambiguidade; áudio mantido")
            except CommandError as exc:
                LOG.warning("Não foi possível trocar o áudio: %s", exc)
            if config.cec_on:
                try:
                    run(config.cec_on, timeout=20)
                    data["cec_enabled"] = True
                    self._save(data)
                except CommandError as exc:
                    LOG.warning("Comando CEC falhou: %s", exc)
            if config.launcher_start:
                try:
                    subprocess.Popen(config.launcher_start, start_new_session=True, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, env=host_environment())
                    data["launcher_started"] = True
                    self._save(data)
                except OSError as exc:
                    LOG.warning("Launcher não iniciou: %s", exc)
            if config.custom_launcher_enabled:
                try:
                    process = subprocess.Popen(
                        custom_launcher_command(config.custom_launcher_path, config.custom_launcher_args),
                        start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        env=host_environment())
                    if config.custom_launcher_close:
                        data["custom_launcher_process"] = _process_identity(process.pid)
                        self._save(data)
                        if data["custom_launcher_process"] is None:
                            LOG.warning("Não foi possível registrar a identidade do inicializador; encerramento automático indisponível")
                    LOG.info("Outro inicializador aberto: %s", config.custom_launcher_path)
                except OSError as exc:
                    LOG.warning("Outro inicializador não iniciou: %s", exc)
        except Exception:
            try:
                self.restore()
            except Exception:
                LOG.exception("Falha também na restauração; estado salvo em %s", self.path)
            raise

    def restore(self) -> bool:
        if not self.pending():
            return False
        data = self._load()
        # Restore the TV volume before disabling its HDMI output removes the
        # sink. Restore again after profiles return to recover the PC channels.
        if data.get("audio_volumes"):
            try:
                audio.restore_volumes(data["audio_volumes"])
            except CommandError as exc:
                LOG.warning("Não foi possível restaurar volumes de áudio: %s", exc)
        current = displays.capture()
        plan = displays.restore_plan(data["display"], current, data["desktop_output"])
        displays.apply(plan)
        after = displays.capture()
        if not displays.output(after, data["desktop_output"]).get("enabled"):
            raise RuntimeError("monitor principal não foi restaurado; estado preservado")
        for previous in data["display"]["outputs"]:
            current_output = next((x for x in after["outputs"] if x.get("name") == previous.get("name")), None)
            if current_output and current_output.get("connected") and current_output.get("enabled") != previous.get("enabled"):
                raise RuntimeError(f"saída {previous['name']} não foi restaurada; estado preservado")
        self._restore_hdr(data["display"], after)
        original_sink = data.get("audio_sink", "")
        if data.get("audio_profiles"):
            try:
                audio.restore_profiles(data["audio_profiles"])
            except CommandError as exc:
                LOG.warning("Não foi possível restaurar perfis de áudio: %s", exc)
        if data.get("audio_volumes"):
            try:
                audio.restore_volumes(data["audio_volumes"])
            except CommandError as exc:
                LOG.warning("Não foi possível restaurar volumes após restaurar perfis: %s", exc)
        if original_sink:
            try:
                audio.set_default(original_sink)
            except CommandError as exc:
                LOG.warning("Não foi possível restaurar áudio: %s", exc)
        for enabled_key, command_key in (("launcher_started", "launcher_stop"), ("cec_enabled", "cec_off")):
            command = data.get(command_key, [])
            if data.get(enabled_key) and command:
                try:
                    run(command, timeout=20)
                except CommandError as exc:
                    LOG.warning("Comando de encerramento falhou: %s", exc)
        _stop_owned_launcher(data.get("custom_launcher_process"))
        self.path.unlink()
        return True
