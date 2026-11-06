"""Test the same AppImage in clean userlands, without host graphics or audio."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "debian12": "docker.io/library/debian:12-slim",
    "debian13": "docker.io/library/debian:13-slim",
    "ubuntu2404": "docker.io/library/ubuntu:24.04",
    "ubuntu2604": "docker.io/library/ubuntu:26.04",
    "fedora44": "registry.fedoraproject.org/fedora:44",
    "arch": "docker.io/library/archlinux:latest",
}


def main() -> None:
    manifest = json.loads((ROOT / "dist/build-info.json").read_text())
    artifact = ROOT / f"dist/CouchPad-{manifest['version']}-x86_64.AppImage"
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if checksum != manifest["sha256"]:
        raise SystemExit("AppImage não corresponde ao manifesto")
    cases = sys.argv[1:] or list(CASES)
    if set(cases) - CASES.keys():
        raise SystemExit(f"Casos válidos: {', '.join(CASES)}")
    logs = ROOT / ".build/runtime-qa"
    logs.mkdir(parents=True, exist_ok=True)

    def check(name: str) -> dict:
        command = (
            "cat /etc/os-release; getconf GNU_LIBC_VERSION; "
            f"/artifacts/{artifact.name} --appimage-extract-and-run --version; v=$?; "
            f"/artifacts/{artifact.name} --appimage-extract-and-run --runtime-check; r=$?; "
            "echo COUCHPAD_VERSION_EXIT=$v; echo COUCHPAD_RUNTIME_EXIT=$r; "
            'test "$v" = 0 && test "$r" = 0'
        )
        result = subprocess.run([
            "podman", "run", "--rm", "--network=none",
            "-v", f"{ROOT / 'dist'}:/artifacts:ro", CASES[name], "sh", "-c", command,
        ], capture_output=True, text=True)
        output = result.stdout + result.stderr
        (logs / f"{name}.log").write_text(output)
        inspect = subprocess.run(["podman", "image", "inspect", CASES[name],
                                  "--format", "{{.Digest}}"], capture_output=True, text=True)
        record = {"name": name, "image": CASES[name], "image_digest": inspect.stdout.strip(),
                  "passed": result.returncode == 0, "exit_code": result.returncode,
                  "output": output}
        print(f"{name}: {'PASS' if record['passed'] else 'FAIL'}", flush=True)
        return record

    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(check, cases))
    (ROOT / "dist/runtime-results.json").write_text(json.dumps({
        "artifact": artifact.name, "sha256": checksum,
        "scope": "clean userland loading and GTK/SVG runtime; no desktop/hardware automation",
        "cases": records,
    }, ensure_ascii=False, indent=2) + "\n")
    if not all(record["passed"] for record in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
