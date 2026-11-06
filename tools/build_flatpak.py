"""Export a local Flatpak bundle containing the Debian-built native payload.

No SDK/compiler is needed: the payload was already compiled in Debian 12.
The Flatpak runtime provides only the launcher; desktop integration runs on host.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ID = "io.github.matheusrmello.CouchPad"
RUNTIME_BRANCH = "25.08"


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerar o repositório e o bundle Flatpak do CouchPad")
    parser.add_argument('--repo-only', action='store_true', help='Gerar somente o repositório local, sem compactar o bundle')
    args = parser.parse_args()
    if platform.machine() != "x86_64":
        raise SystemExit("O payload atual requer x86_64")
    manifest = json.loads((ROOT / "dist/build-info.json").read_text())
    if tuple(map(int, manifest["required_glibc_symbols"].split("."))) > (2, 36):
        raise SystemExit("Reconstrua primeiro com tools/build_portable.py (glibc <= 2.36)")
    payload = ROOT / ".build/appimage/CouchPad.AppDir/usr/bin"
    if not (payload / "couchpad").is_file():
        raise SystemExit("Payload ausente: execute tools/build_portable.py")
    build = ROOT / ".build/flatpak/app"
    repo = ROOT / ".build/flatpak/repo"
    if build.exists():
        shutil.rmtree(build)
    files = build / "files"
    (files / "bin").mkdir(parents=True)
    shutil.copytree(payload, files / "lib/couchpad", symlinks=True)
    wrapper = files / "bin/couchpad"
    shutil.copy2(ROOT / "packaging/flatpak/couchpad", wrapper)
    wrapper.chmod(0o755)
    for suffix, directory in (("desktop", "applications"), ("metainfo.xml", "metainfo")):
        target = files / "share" / directory
        target.mkdir(parents=True)
        shutil.copy2(ROOT / f"packaging/flatpak/{APP_ID}.{suffix}", target)
    icons = files / "share/icons/hicolor/scalable/apps"
    icons.mkdir(parents=True)
    shutil.copy2(ROOT / "shiftpad_linux/assets/couchpad.svg", icons / f"{APP_ID}.svg")
    shutil.copytree(ROOT / ".build/appimage/CouchPad.AppDir/usr/share/licenses",
                    files / "share/licenses", symlinks=True)
    docs = files / "share/doc/couchpad"
    docs.mkdir(parents=True)
    shutil.copy2(ROOT / "LICENSE", docs)
    shutil.copy2(ROOT / "packaging/flatpak/README.md", docs)
    (build / "metadata").write_text(
        f"[Application]\nname={APP_ID}\nruntime=org.freedesktop.Platform/x86_64/{RUNTIME_BRANCH}\n"
        f"sdk=org.freedesktop.Sdk/x86_64/{RUNTIME_BRANCH}\n")
    subprocess.run(["flatpak", "build-finish", "--command=couchpad",
                    "--talk-name=org.freedesktop.Flatpak", str(build)], check=True)
    subprocess.run(["flatpak", "build-export", "--arch=x86_64", str(repo), str(build), "beta"], check=True)
    if args.repo_only:
        print(repo)
        return
    artifact = ROOT / f"dist/CouchPad-{manifest['version']}-x86_64.flatpak"
    subprocess.run(["flatpak", "build-bundle", "--arch=x86_64",
                    "--runtime-repo=https://flathub.org/repo/flathub.flatpakrepo",
                    str(repo), str(artifact), APP_ID, "beta"], check=True)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    artifact.with_suffix(".flatpak.sha256").write_text(f"{digest}  {artifact.name}\n")
    (ROOT / "dist/flatpak-build-info.json").write_text(json.dumps({
        "app_id": APP_ID, "version": manifest["version"], "branch": "beta",
        "runtime": f"org.freedesktop.Platform/{RUNTIME_BRANCH}",
        "execution": "native payload on host via flatpak-spawn --host",
        "host_glibc_required": manifest["required_glibc_symbols"],
        "permissions": ["org.freedesktop.Flatpak=talk"],
        "sha256": digest, "size_bytes": artifact.stat().st_size,
    }, ensure_ascii=False, indent=2) + "\n")
    print(artifact)


if __name__ == "__main__":
    main()
