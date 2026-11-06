from __future__ import annotations

import subprocess
import os
import sys


class CommandError(RuntimeError):
    pass


def host_environment() -> dict[str, str]:
    """Keep bundled libraries out of Steam, KScreen and other host programs."""
    env = os.environ.copy()
    if getattr(sys, "frozen", False):
        if env.pop("COUCHPAD_PRIVATE_QT_BACKEND", "") == "1":
            env.pop("QT_QUICK_BACKEND", None)
        original = env.pop("LD_LIBRARY_PATH_ORIG", "")
        if original:
            env["LD_LIBRARY_PATH"] = original
        else:
            env.pop("LD_LIBRARY_PATH", None)
        root = str(getattr(sys, "_MEIPASS", ""))
        for key in ("PATH", "XDG_DATA_DIRS", "GI_TYPELIB_PATH", "GIO_EXTRA_MODULES"):
            if root and key in env:
                value = ":".join(part for part in env[key].split(":") if not part.startswith(root))
                if value:
                    env[key] = value
                else:
                    env.pop(key, None)
        for key in ("GDK_PIXBUF_MODULE_FILE", "GIO_MODULE_DIR", "GTK_DATA_PREFIX",
                    "GTK_EXE_PREFIX", "GSETTINGS_SCHEMA_DIR", "FONTCONFIG_PATH", "FONTCONFIG_FILE"):
            if root and env.get(key, "").startswith(root):
                env.pop(key, None)
        env.pop("GLYCIN_DATA_DIR", None)
    return env


def run(args: list[str] | tuple[str, ...], timeout: float = 15) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False, timeout=timeout,
                                env=host_environment())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CommandError(f"falha ao executar {args[0]}: {exc}") from exc
    if result.returncode:
        raise CommandError(f"{' '.join(args)}: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout
