"""Relocate Glycin helpers used by newer GdkPixbuf releases."""

import atexit
import os
from pathlib import Path
import shutil
import sys
import tempfile

root = Path(sys._MEIPASS)
fonts = root / "etc/fonts"
if (fonts / "fonts.conf").is_file():
    os.environ["FONTCONFIG_PATH"] = str(fonts)
    os.environ["FONTCONFIG_FILE"] = str(fonts / "fonts.conf")
source = root / "share/glycin-loaders/2+/conf.d"
if source.is_dir():
    temporary = Path(tempfile.mkdtemp(prefix="couchpad-glycin-"))
    destination = temporary / "glycin-loaders/2+/conf.d"
    destination.mkdir(parents=True)
    for config in source.glob("*.conf"):
        text = config.read_text().replace("/usr/lib/glycin-loaders/2+/",
                                          str(root / "lib/glycin-loaders/2+") + "/")
        (destination / config.name).write_text(text)
    os.environ["GLYCIN_DATA_DIR"] = str(temporary)
    os.environ["PATH"] = str(root / "bin") + os.pathsep + os.environ.get("PATH", "")
    atexit.register(shutil.rmtree, temporary, ignore_errors=True)
