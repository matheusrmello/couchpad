"""Build the AppImage in Debian 12 (glibc 2.36), never with host libraries."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "localhost/couchpad-build:debian12"


def main() -> None:
    subprocess.run(["podman", "build", "-t", IMAGE, "-f",
                    str(ROOT / "packaging/appimage/Containerfile"), str(ROOT)], check=True)
    subprocess.run([
        "podman", "run", "--rm", "--userns=keep-id",
        "-v", f"{ROOT}:/src:rw", "-e", "COUCHPAD_MAX_GLIBC=2.36",
        "-e", "XDG_CACHE_HOME=/src/.build/cache", IMAGE,
        "sh", "-ec",
        "mkdir -p .build/downloads; "
        "if ! test -f .build/downloads/appimagetool-x86_64.AppImage; then "
        "curl -fL --retry 3 https://github.com/AppImage/appimagetool/releases/download/1.9.1/"
        "appimagetool-x86_64.AppImage -o .build/downloads/appimagetool-x86_64.AppImage.part; "
        "mv .build/downloads/appimagetool-x86_64.AppImage.part .build/downloads/appimagetool-x86_64.AppImage; fi; "
        "chmod +x .build/downloads/appimagetool-x86_64.AppImage; "
        "python tools/build_appimage.py",
    ], check=True)


if __name__ == "__main__":
    main()
