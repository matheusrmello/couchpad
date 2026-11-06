"""Build the local x86_64 GTK beta. Requires PyInstaller in the selected Python."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shiftpad_linux import __version__


def main() -> None:
    if platform.machine() != "x86_64":
        raise SystemExit("Este roteiro da beta local requer x86_64")
    build = ROOT / ".build/appimage"
    output = ROOT / "dist"
    tool = ROOT / ".build/downloads/appimagetool-x86_64.AppImage"
    if not tool.exists():
        raise SystemExit("Baixe appimagetool-x86_64.AppImage em .build/downloads primeiro; veja packaging/appimage/README.md")
    tool_sha256 = hashlib.sha256(tool.read_bytes()).hexdigest()
    if tool_sha256 != "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0":
        raise SystemExit("SHA-256 de appimagetool 1.9.1 x86_64 não corresponde ao esperado")
    output.mkdir(exist_ok=True)
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", str(build / "frozen"), "--workpath", str(build / "work"),
        str(ROOT / "packaging/appimage/couchpad.spec"),
    ], cwd=ROOT, check=True)
    appdir = build / "CouchPad.AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)
    (appdir / "usr").mkdir(parents=True)
    shutil.copytree(build / "frozen/couchpad", appdir / "usr/bin", symlinks=True)
    for name in ("AppRun", "couchpad.desktop"):
        shutil.copy2(ROOT / "packaging/appimage" / name, appdir / name)
    (appdir / "AppRun").chmod(0o755)
    shutil.copy2(ROOT / "shiftpad_linux/assets/couchpad.svg", appdir / "couchpad.svg")
    (appdir / ".DirIcon").symlink_to("couchpad.svg")
    docs = appdir / "usr/share/doc/couchpad"
    docs.mkdir(parents=True)
    shutil.copy2(ROOT / "packaging/appimage/README.md", docs / "README.md")
    # Keep dependency notices available in the artifact, without installing files
    # into the host system.
    notices = appdir / "usr/share/licenses"
    for package in ("python", "gtk3", "glib2", "gdk-pixbuf2", "pango", "cairo",
                    "python-gobject", "python-cairo", "python-evdev", "pyinstaller",
                    "glycin", "glycin-loaders", "bubblewrap"):
        source = Path("/usr/share/licenses") / package
        if source.is_dir():
            shutil.copytree(source, notices / package, dirs_exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", docs / "LICENSE")
    if Path("/usr/share/doc").is_dir() and Path("/etc/debian_version").exists():
        for copyright in Path("/usr/share/doc").glob("*/copyright"):
            destination = notices / copyright.parent.name
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(copyright, destination / "copyright")
    glibc_versions = set()
    for binary in (appdir / "usr/bin").rglob("*"):
        if not binary.is_file() or binary.is_symlink():
            continue
        with binary.open("rb") as file:
            if file.read(4) != b"\x7fELF":
                continue
        info = subprocess.run(["readelf", "--version-info", str(binary)],
                              capture_output=True, text=True, check=False).stdout
        glibc_versions.update(re.findall(r"GLIBC_(\d+\.\d+(?:\.\d+)?)", info))
    required_glibc = max(glibc_versions, key=lambda value: tuple(map(int, value.split("."))))
    maximum = os.environ.get("COUCHPAD_MAX_GLIBC", "2.36")
    if tuple(map(int, required_glibc.split("."))) > tuple(map(int, maximum.split("."))):
        raise SystemExit(f"Build exige glibc {required_glibc}, acima do limite {maximum}. "
                         "Use python3 tools/build_portable.py (Debian 12).")
    artifact = output / f"CouchPad-{__version__}-x86_64.AppImage"
    subprocess.run([str(tool), "--appimage-extract-and-run", "--no-appstream",
                    str(appdir), str(artifact)], check=True)
    artifact.chmod(0o755)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (output / f"{artifact.name}.sha256").write_text(f"{digest}  {artifact.name}\n")
    manifest = {"version": __version__, "architecture": platform.machine(),
                "build_host": platform.platform(), "libc": platform.libc_ver(),
                "required_glibc_symbols": required_glibc,
                "python": platform.python_version(),
                "appimagetool_sha256": tool_sha256,
                "size_bytes": artifact.stat().st_size, "sha256": digest,
                "scope": "Beta local: KDE Plasma/Wayland, XWayland, kscreen-doctor, pactl",
                "bundled": ["Python", "Qt Quick", "PySide6", "GTK3", "PyGObject", "pycairo", "evdev", "SVG assets", "image loaders"],
                "unverified": ["other Linux distributions", "GNOME", "other compositors"]}
    (output / "build-info.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(artifact)


if __name__ == "__main__":
    main()
