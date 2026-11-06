from pathlib import Path

root = Path(SPECPATH).resolve().parents[1]
binaries = []
# PyInstaller excludes these display-client libraries by default. GTK links
# them even when the application selects X11; clean userlands may lack them.
for name in ("libwayland-client.so.0", "libwayland-cursor.so.0",
             "libwayland-egl.so.1", "libxcb.so.1"):
    library = Path("/usr/lib/x86_64-linux-gnu") / name
    if library.is_file():
        binaries.append((str(library), "."))
datas = [(str(root / "shiftpad_linux/assets"), "shiftpad_linux/assets"),
         (str(root / "shiftpad_linux/qml"), "shiftpad_linux/qml")]
# Match the bundled fontconfig library with its own configuration. New host
# fontconfig rules may use syntax unsupported by Debian 12's library.
if Path("/etc/fonts/fonts.conf").is_file():
    datas.append(("/etc/fonts/fonts.conf", "etc/fonts"))
    for config in Path("/etc/fonts/conf.d").glob("*.conf"):
        datas.append((str(config.resolve()), "etc/fonts/conf.d"))
if Path("/usr/share/fonts/truetype/dejavu").is_dir():
    datas.append(("/usr/share/fonts/truetype/dejavu", "share/fonts/truetype/dejavu"))
for name in ("glycin-svg", "glycin-image-rs"):
    helper = Path("/usr/lib/glycin-loaders/2+") / name
    config = Path("/usr/share/glycin-loaders/2+/conf.d") / f"{name}.conf"
    if helper.is_file() and config.is_file():
        binaries.append((str(helper), "lib/glycin-loaders/2+"))
        datas.append((str(config), "share/glycin-loaders/2+/conf.d"))
if binaries and Path("/usr/bin/bwrap").is_file():
    binaries.append(("/usr/bin/bwrap", "bin"))
a = Analysis(
    [str(root / "packaging/appimage/entry.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    runtime_hooks=[str(root / "packaging/appimage/runtime_hook.py")],
    hiddenimports=["gi.repository.Gtk", "gi.repository.Gdk", "gi.repository.GdkPixbuf",
                   "gi.repository.Gio", "gi.repository.GLib", "gi.repository.GObject",
                   "gi._gi_cairo", "cairo", "evdev"],
    hooksconfig={"gi": {"icons": ["Adwaita", "hicolor"], "themes": ["Adwaita"],
                         "languages": ["pt", "pt_BR", "en"],
                         "module-versions": {"Gtk": "3.0", "Gdk": "3.0"}}},
    excludes=["tkinter", "pytest", "numpy", "matplotlib", "PyQt5", "PyQt6"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="couchpad",
          debug=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="couchpad")
